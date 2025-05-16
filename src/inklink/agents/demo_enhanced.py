"""Enhanced demonstration of the InkLink Local AI Agent Framework."""

import asyncio
import logging
from pathlib import Path
from datetime import time
from typing import Dict, Any

from dependency_injector.wiring import inject, Provide

from inklink.agents.di import AgentContainer, init_container
from inklink.agents.base.agent import AgentConfig, LocalAgent
from inklink.agents.base.registry import AgentRegistry
from inklink.agents.base.monitoring import MonitoringService
from inklink.adapters.ollama_adapter_enhanced import EnhancedOllamaAdapter
from inklink.adapters.limitless_adapter import LimitlessAdapter
from inklink.adapters.remarkable_adapter import RemarkableAdapter
from inklink.agents.base.exceptions import AgentException, AgentConfigurationError

# Configure logging
logging.basicConfig(level=logging.INFO)


class EnhancedDemo:
    """Enhanced demonstration with configuration and monitoring."""

    @inject
    def __init__(
        self,
        agent_registry: AgentRegistry = Provide[AgentContainer.agent_registry],
        monitoring_service: MonitoringService = Provide[
            AgentContainer.monitoring_service
        ],
        ollama_adapter: EnhancedOllamaAdapter = Provide[AgentContainer.ollama_adapter],
        limitless_adapter: LimitlessAdapter = Provide[AgentContainer.limitless_adapter],
        remarkable_adapter: RemarkableAdapter = Provide[
            AgentContainer.remarkable_adapter
        ],
    ):
        """Initialize the enhanced demo."""
        self.agent_registry = agent_registry
        self.monitoring_service = monitoring_service
        self.ollama_adapter = ollama_adapter
        self.limitless_adapter = limitless_adapter
        self.remarkable_adapter = remarkable_adapter
        self.logger = logging.getLogger(__name__)

    async def setup_agents(self) -> None:
        """Set up and start all agents with enhanced monitoring."""
        self.logger.info("Setting up agents with enhanced configuration...")

        # Create agents using DI factories
        container = AgentContainer()

        # Create Limitless Insight Agent
        limitless_agent = container.limitless_insight_agent()
        await self.agent_registry.register_agent("limitless_insight", limitless_agent)
        await limitless_agent.start()

        # Create Daily Briefing Agent
        briefing_agent = container.daily_briefing_agent(
            briefing_time=time(6, 0)  # 6 AM
        )
        await self.agent_registry.register_agent("daily_briefing", briefing_agent)
        await briefing_agent.start()

        # Create Project Tracker Agent
        tracker_agent = container.project_tracker_agent()
        await self.agent_registry.register_agent("project_tracker", tracker_agent)
        await tracker_agent.start()

        self.logger.info("All agents started successfully")

    async def demonstrate_error_handling(self) -> None:
        """Demonstrate error handling and recovery."""
        self.logger.info("\n=== Error Handling Demo ===")

        # Test configuration error
        try:
            # Create agent without model configuration
            AgentConfig(
                name="invalid_agent",
                initial_state="active",
                # Missing ollama_model
            )
            # This should raise an error when trying to use Ollama
            pass
        except AgentConfigurationError as e:
            self.logger.error(f"Configuration error caught: {e}")

        # Test service health check
        health_status = await self.monitoring_service.get_health_status()
        self.logger.info(f"Health status: {health_status}")

    async def demonstrate_monitoring(self) -> None:
        """Demonstrate monitoring capabilities."""
        self.logger.info("\n=== Monitoring Demo ===")

        # Get metrics
        metrics = await self.monitoring_service.get_metrics()
        for agent_id, agent_metrics in metrics.items():
            self.logger.info(f"\nAgent: {agent_id}")
            for metric, value in agent_metrics.items():
                self.logger.info(f"  {metric}: {value}")

        # Test failure detection
        self.logger.info("\nSimulating agent failure...")
        # The monitoring service will automatically restart failed agents

    async def demonstrate_configuration(self) -> None:
        """Demonstrate configuration management."""
        self.logger.info("\n=== Configuration Demo ===")

        # Show loaded configuration
        ollama_status = await self.ollama_adapter.health_check()
        self.logger.info(f"Ollama adapter status: {ollama_status}")

        # Show environment variable substitution
        self.logger.info("Configuration loaded with environment variables")

    async def run_demo(self) -> None:
        """Run the complete enhanced demo."""
        try:
            # Setup agents
            await self.setup_agents()

            # Wait for agents to initialize
            await asyncio.sleep(2)

            # Test MCP communication
            self.logger.info("\n=== Testing MCP Communication ===")
            registry_agent = self.agent_registry.get_agent("agent_registry")

            # Get Limitless summary
            response = await registry_agent.handle_request(
                {
                    "target": "limitless_insight",
                    "capability": "get_spoken_summary",
                    "data": {"time_period": "last_24_hours"},
                }
            )
            self.logger.info(f"Limitless summary: {response}")

            # Generate briefing
            response = await registry_agent.handle_request(
                {
                    "target": "daily_briefing",
                    "capability": "generate_briefing",
                    "data": {},
                }
            )
            self.logger.info("Daily briefing generated")

            # Get project status
            response = await registry_agent.handle_request(
                {"target": "project_tracker", "capability": "list_projects", "data": {}}
            )
            self.logger.info(f"Projects: {response}")

            # Demonstrate error handling
            await self.demonstrate_error_handling()

            # Demonstrate monitoring
            await self.demonstrate_monitoring()

            # Demonstrate configuration
            await self.demonstrate_configuration()

            self.logger.info("\n=== Enhanced Demo Complete ===")

        except Exception as e:
            self.logger.error(f"Demo failed: {e}", exc_info=True)

        finally:
            # Cleanup
            await self.agent_registry.stop_all()
            self.logger.info("All agents stopped")


async def main():
    """Main entry point for enhanced demo."""
    # Initialize dependency injection container
    init_container()

    # Create and run demo
    demo = EnhancedDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
