"""Example demonstrating the InkLink Agent Framework."""

import asyncio
import logging
from pathlib import Path

from inklink.adapters.limitless_adapter import LimitlessAdapter
from inklink.adapters.ollama_adapter import OllamaAdapter
from inklink.adapters.remarkable_adapter import RemarkableAdapter
from inklink.agents.base.agent import AgentConfig
from inklink.agents.base.lifecycle import AgentLifecycle
from inklink.agents.base.registry import AgentRegistry
from inklink.agents.core import (
    DailyBriefingAgent,
    LimitlessContextualInsightAgent,
    ProactiveProjectTrackerAgent,
)


class AgentFactory:
    """Factory for creating agents with their dependencies."""

    def __init__(
        self,
        ollama_adapter: OllamaAdapter,
        limitless_adapter: LimitlessAdapter,
        remarkable_adapter: RemarkableAdapter,
        storage_base: Path,
    ):
        """Initialize the factory with shared dependencies."""
        self.ollama_adapter = ollama_adapter
        self.limitless_adapter = limitless_adapter
        self.remarkable_adapter = remarkable_adapter
        self.storage_base = storage_base

    def create_limitless_agent(
        self, config: AgentConfig
    ) -> LimitlessContextualInsightAgent:
        """Create a Limitless insight agent with its dependencies."""
        return LimitlessContextualInsightAgent(
            config,
            self.limitless_adapter,
            self.ollama_adapter,
            self.storage_base / "limitless",
        )

    def create_daily_briefing_agent(self, config: AgentConfig) -> DailyBriefingAgent:
        """Create a daily briefing agent with its dependencies."""
        return DailyBriefingAgent(
            config,
            self.ollama_adapter,
            self.remarkable_adapter,
            self.storage_base / "briefings",
        )

    def create_project_tracker_agent(
        self, config: AgentConfig
    ) -> ProactiveProjectTrackerAgent:
        """Create a project tracker agent with its dependencies."""
        return ProactiveProjectTrackerAgent(
            config, self.ollama_adapter, self.storage_base / "projects"
        )


async def main():
    """Run the agent framework demo."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Initialize adapters
    ollama_adapter = OllamaAdapter()
    limitless_adapter = LimitlessAdapter()  # Would need proper initialization
    remarkable_adapter = RemarkableAdapter()  # Would need proper initialization

    # Setup storage
    storage_path = Path.home() / ".inklink" / "agent_data"
    storage_path.mkdir(parents=True, exist_ok=True)

    # Create factory
    factory = AgentFactory(
        ollama_adapter=ollama_adapter,
        limitless_adapter=limitless_adapter,
        remarkable_adapter=remarkable_adapter,
        storage_base=storage_path,
    )

    # Create agent registry
    registry = AgentRegistry()

    # Create agent configurations
    limitless_config = AgentConfig(
        name="limitless_insight",
        description="Processes Limitless pendant data for insights",
        version="1.0.0",
        capabilities=["spoken_summary", "action_items", "context_search"],
        ollama_model="llama3:8b",
        mcp_enabled=True,
    )

    briefing_config = AgentConfig(
        name="daily_briefing",
        description="Generates daily briefings with personalized context",
        version="1.0.0",
        capabilities=["generate_briefing", "briefing_status"],
        ollama_model="llama3:8b",
        mcp_enabled=True,
    )

    tracker_config = AgentConfig(
        name="project_tracker",
        description="Tracks projects and commitments",
        version="1.0.0",
        capabilities=["project_status", "commitment_tracking"],
        ollama_model="llama3:8b",
        mcp_enabled=True,
    )

    # Create agents using factory
    limitless_agent = factory.create_limitless_agent(limitless_config)
    briefing_agent = factory.create_daily_briefing_agent(briefing_config)
    tracker_agent = factory.create_project_tracker_agent(tracker_config)

    # Register the properly initialized agents
    # This avoids the two-phase initialization antipattern by using the factory pattern
    await registry.register_agent(limitless_agent)
    await registry.register_agent(briefing_agent)
    await registry.register_agent(tracker_agent)

    # Create lifecycle manager
    lifecycle = AgentLifecycle(registry)

    print("Starting InkLink Agent Framework...")
    print(f"Registered agents: {registry.get_registered_classes()}")

    # Run the lifecycle manager
    try:
        await lifecycle.run()
    except KeyboardInterrupt:
        print("\nShutting down agents...")
        await lifecycle.shutdown()

    print("Agent framework demo completed.")


if __name__ == "__main__":
    asyncio.run(main())
