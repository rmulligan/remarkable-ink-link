"""Enhanced agent framework demo using configuration and DI."""

import asyncio
import logging
import os

from inklink.agents.base.monitoring import MonitoringService
from inklink.agents.config import config_loader
from inklink.agents.di import container, setup_agents


async def run_monitoring(monitoring_service: MonitoringService, registry):
    """Run the monitoring service."""
    while True:
        try:
            agents = await registry.list_agents()

            for agent in agents:
                # Perform health check
                health_check = await monitoring_service.check_agent_health(agent)

                # Record health check
                metrics = monitoring_service.get_or_create_metrics(agent.config.name)
                metrics.health_checks.append(health_check)

                # Log status
                status_summary = monitoring_service.get_agent_status_summary(
                    agent.config.name
                )
                logging.info(f"Agent {agent.config.name}: {status_summary}")

            # Cleanup old metrics
            monitoring_service.cleanup_old_metrics()

            # Wait for next check
            await asyncio.sleep(monitoring_service.health_check_interval)

        except Exception as e:
            logging.error(f"Error in monitoring loop: {e}")
            await asyncio.sleep(10)


async def main():
    """Run the enhanced agent framework demo."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Set environment variables for demo (in production, these would be set externally)
    os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
    os.environ["LIMITLESS_API_KEY"] = "your-limitless-api-key"
    os.environ["REMARKABLE_DEVICE_TOKEN"] = "your-remarkable-token"

    # Load configuration
    config = config_loader.load()
    monitoring_config = config_loader.get_monitoring_config()

    print("=== Enhanced Agent Framework Demo ===")
    print(f"Framework version: {config['framework']['version']}")
    print(f"Storage base: {config['framework']['storage_base']}")

    # Setup agents with dependency injection
    setup_agents()

    # Get registry and lifecycle from DI container
    registry = container.agent_registry()
    lifecycle = container.agent_lifecycle()

    # Create monitoring service
    monitoring_service = MonitoringService(
        health_check_interval=monitoring_config["health_check_interval"]
    )

    # Print registered agents
    print("\nRegistered agents:")
    agents_list = await registry.list_agents()
    for agent in agents_list:
        print(f"  - {agent.config.name}: {agent.config.description}")

    # Start monitoring
    monitoring_task = asyncio.create_task(run_monitoring(monitoring_service, registry))

    try:
        # Start all agents
        await lifecycle.startup()

        print("\nAll agents started. Running...")

        # Demonstrate inter-agent communication
        await asyncio.sleep(5)

        print("\nDemonstrating inter-agent communication...")

        # Get agents
        limitless_agent = await registry.get_agent("limitless_insight")
        briefing_agent = await registry.get_agent("daily_briefing")

        if limitless_agent and briefing_agent:
            # Simulate a request to generate a briefing
            result = await briefing_agent.handle_request({"type": "generate_briefing"})
            print(f"Briefing generation result: {result}")

        # Let it run for a while
        await asyncio.sleep(30)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        monitoring_task.cancel()
        await lifecycle.shutdown()

    print("\nDemo completed.")


if __name__ == "__main__":
    asyncio.run(main())
