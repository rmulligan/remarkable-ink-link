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

    # Create agent registry
    registry = AgentRegistry()

    # Register agent classes
    registry.register_agent_class(LimitlessContextualInsightAgent)
    registry.register_agent_class(DailyBriefingAgent)
    registry.register_agent_class(ProactiveProjectTrackerAgent)

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

    # Create agents
    limitless_agent = await registry.create_agent(
        "LimitlessContextualInsightAgent", limitless_config
    )

    briefing_agent = await registry.create_agent("DailyBriefingAgent", briefing_config)

    tracker_agent = await registry.create_agent(
        "ProactiveProjectTrackerAgent", tracker_config
    )

    # Initialize agents with required dependencies
    limitless_agent.__init__(
        limitless_config, limitless_adapter, ollama_adapter, storage_path / "limitless"
    )

    briefing_agent.__init__(
        briefing_config, ollama_adapter, remarkable_adapter, storage_path / "briefings"
    )

    tracker_agent.__init__(tracker_config, ollama_adapter, storage_path / "projects")

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
