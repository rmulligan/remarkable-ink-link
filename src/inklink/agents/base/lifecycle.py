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

            self.logger.info("Agent lifecycle started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start agent lifecycle: {e}")
            await self.shutdown()
            raise

    async def shutdown(self) -> None:
        """Shut down all agents gracefully."""
        if not self._running:
            return

        self.logger.info("Shutting down agent lifecycle")
        self._running = False

        try:
            # Stop all running agents
            await self.registry.stop_all()

            # Run any shutdown handlers
            for handler in reversed(self._shutdown_handlers):
                if hasattr(handler, "__aexit__"):
                    await handler.__aexit__(None, None, None)

            self.logger.info("Agent lifecycle shut down successfully")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            raise

    async def run(self) -> None:
        """Run the lifecycle manager."""
        await self.startup()

        try:
            # Keep running until shutdown is called
            while self._running:
                # Monitor agent health
                await self._monitor_agents()
                await asyncio.sleep(5)  # Check every 5 seconds

        finally:
            await self.shutdown()

    async def _monitor_agents(self) -> None:
        """Monitor agent health and restart if necessary."""
        agents = await self.registry.list_agents()

        for agent in agents:
            state = agent.get_state()

            # Restart agents that have errored
            if state == "error":
                self.logger.warning(
                    f"Agent '{agent.config.name}' in error state, attempting restart"
                )
                await self._restart_agent(agent.config.name)

    @retry(
        max_attempts=3,
        base_delay=1.0,
        exceptions=(Exception,),
        on_retry=lambda e, attempt: logging.getLogger("agent.lifecycle").warning(
            f"Retry attempt {attempt} for agent restart: {e}"
        ),
    )
    async def _restart_agent(self, agent_name: str) -> None:
        """Restart an agent with retry logic."""
        await self.registry.stop_agent(agent_name)
        await self.registry.start_agent(agent_name)
        self.logger.info(f"Successfully restarted agent '{agent_name}'")

    def add_shutdown_handler(self, handler: Callable) -> None:
        """Add a shutdown handler."""
        self._shutdown_handlers.append(handler)

    def remove_shutdown_handler(self, handler: Callable) -> None:
        """Remove a shutdown handler."""
        self._shutdown_handlers.remove(handler)

    def is_running(self) -> bool:
        """Check if the lifecycle manager is running."""
        return self._running

    def __repr__(self) -> str:
        """String representation of the lifecycle manager."""
        return f"<AgentLifecycle running={self._running}>"
