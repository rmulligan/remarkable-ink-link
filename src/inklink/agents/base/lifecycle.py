"""Agent lifecycle management."""

import asyncio
import logging
import signal
from typing import Callable, List, Optional

from inklink.utils.retry import retry
from .registry import AgentRegistry


class AgentLifecycle:
    """Manages the lifecycle of all agents."""

    def __init__(self, registry: AgentRegistry):
        """Initialize the lifecycle manager."""
        self.logger = logging.getLogger("agent.lifecycle")
        self.registry = registry
        self._shutdown_handlers: List[Callable] = []
        self._running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating shutdown")
        asyncio.create_task(self.shutdown())

    async def startup(self) -> None:
        """Start up all agents and begin monitoring."""
        self.logger.info("Starting agent lifecycle")
        self._running = True

        try:
            # Start all registered agents
            await self.registry.start_all()

            # Run any startup handlers
            for handler in self._shutdown_handlers:
                if hasattr(handler, "__aenter__"):
                    await handler.__aenter__()

        except Exception as e:
            self.logger.error(f"Error during startup: {e}")
            await self.shutdown()
            raise

    async def shutdown(self) -> None:
        """Shut down all agents gracefully."""
        if not self._running:
            return

        self.logger.info("Shutting down agent lifecycle")
        self._running = False

        try:
            # Run shutdown handlers in reverse order
            for handler in reversed(self._shutdown_handlers):
                if hasattr(handler, "__aexit__"):
                    await handler.__aexit__(None, None, None)

            # Stop all agents
            await self.registry.stop_all()

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            raise

    async def run(self) -> None:
        """Run the agent lifecycle."""
        try:
            await self.startup()

            # Keep running until shutdown
            while self._running:
                await asyncio.sleep(1)

                # Perform periodic health checks
                health_reports = await self.registry.check_all_health()

                # Log any unhealthy agents
                for agent_name, health in health_reports.items():
                    if health.status == "unhealthy":
                        self.logger.warning(
                            f"Agent {agent_name} is unhealthy: {health.message}"
                        )

        except Exception as e:
            self.logger.error(f"Error in lifecycle run: {e}")
        finally:
            await self.shutdown()

    def add_shutdown_handler(self, handler: Callable) -> None:
        """Add a shutdown handler."""
        self._shutdown_handlers.append(handler)

    async def restart_agent(self, agent_name: str) -> None:
        """Restart a specific agent."""
        self.logger.info(f"Restarting agent {agent_name}")

        try:
            # Stop the agent
            await self.registry.stop_agent(agent_name)

            # Small delay before restart
            await asyncio.sleep(1)

            # Start the agent again
            await self.registry.start_agent(agent_name)

            self.logger.info(f"Agent {agent_name} restarted successfully")

        except Exception as e:
            self.logger.error(f"Failed to restart agent {agent_name}: {e}")
            raise

    async def health_monitor(self, interval: int = 30) -> None:
        """Monitor agent health periodically."""
        while self._running:
            try:
                # Check health of all agents
                health_reports = await self.registry.check_all_health()

                # Restart unhealthy agents
                for agent_name, health in health_reports.items():
                    if health.status == "unhealthy":
                        self.logger.warning(
                            f"Agent {agent_name} is unhealthy, attempting restart"
                        )
                        await self.restart_agent(agent_name)

                await asyncio.sleep(interval)

            except Exception as e:
                self.logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(interval)

    @retry(max_attempts=3, base_delay=1.0)
    async def resilient_startup(self) -> None:
        """Start up with retry logic."""
        await self.startup()

    async def __aenter__(self):
        """Context manager entry."""
        await self.startup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.shutdown()


class LifecycleContext:
    """Context manager for agent lifecycle."""

    def __init__(self, lifecycle: AgentLifecycle):
        """Initialize the context."""
        self.lifecycle = lifecycle

    async def __aenter__(self):
        """Enter the context."""
        await self.lifecycle.startup()
        return self.lifecycle

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context."""
        await self.lifecycle.shutdown()


async def run_agent_system(
    registry: AgentRegistry, monitor_health: bool = True
) -> None:
    """Run the complete agent system."""
    lifecycle = AgentLifecycle(registry)

    # Create monitoring task if enabled
    monitor_task = None
    if monitor_health:
        monitor_task = asyncio.create_task(lifecycle.health_monitor())

    try:
        # Run the main lifecycle
        await lifecycle.run()

    finally:
        # Cancel monitoring task if it exists
        if monitor_task:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
