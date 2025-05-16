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

    # Initialize adapters with proper configuration
    ollama_adapter = OllamaAdapter(base_url="http://localhost:11434")

    # For demo purposes, using mock configuration
    limitless_adapter = LimitlessAdapter(
        api_key="demo_key", base_url="https://api.limitless.ai"
    )
    remarkable_adapter = RemarkableAdapter(
        rmapi_path="rmapi", upload_folder="/"  # assuming rmapi is in PATH
    )

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

    # Create agents with proper initialization
    # Note: Agents should be created with all required dependencies
    limitless_agent = LimitlessContextualInsightAgent(
        config=limitless_config,
        limitless_adapter=limitless_adapter,
        ollama_adapter=ollama_adapter,
        storage_path=storage_path / "limitless",
    )
    registry._agents[limitless_config.name] = limitless_agent

    briefing_agent = DailyBriefingAgent(
        config=briefing_config,
        ollama_adapter=ollama_adapter,
        remarkable_adapter=remarkable_adapter,
        storage_path=storage_path / "briefings",
    )
    registry._agents[briefing_config.name] = briefing_agent

    tracker_agent = ProactiveProjectTrackerAgent(
        config=tracker_config,
        ollama_adapter=ollama_adapter,
        storage_path=storage_path / "projects",
    )
    registry._agents[tracker_config.name] = tracker_agent

    # Create lifecycle manager
    lifecycle = AgentLifecycle(registry)

    print("Starting InkLink Agent Framework...")
    print(f"Registered agents: {list(registry._agents.keys())}")

    # Run the lifecycle manager
    try:
        await lifecycle.run()
    except KeyboardInterrupt:
        print("\nShutting down agents...")
        await lifecycle.shutdown()

    print("Agent framework demo completed.")


if __name__ == "__main__":
    asyncio.run(main())
