"""Dependency injection for the agent framework."""

from dependency_injector import containers, providers
from pathlib import Path
from typing import Dict, Any

from inklink.adapters.ollama_adapter import OllamaAdapter
from inklink.adapters.limitless_adapter import LimitlessAdapter
from inklink.adapters.remarkable_adapter import RemarkableAdapter
from inklink.adapters.handwriting_adapter import HandwritingAdapter
from inklink.services.remarkable_service import RemarkableService
from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)

from ..config import config_loader
from ..base.registry import AgentRegistry
from ..base.lifecycle import AgentLifecycle
from ..core import (
    LimitlessContextualInsightAgent,
    DailyBriefingAgent,
    ProactiveProjectTrackerAgent,
    ControlCenterAgent,
)


class AgentContainer(containers.DeclarativeContainer):
    """DI container for agent framework."""

    # Configuration
    config = providers.Singleton(lambda: config_loader.load())

    framework_config = providers.Singleton(lambda: config_loader.get_framework_config())

    # Storage paths
    storage_base_path = providers.Singleton(
        lambda: Path(config_loader.get_framework_config()["storage_base"]).expanduser()
    )

    # Adapters
    ollama_adapter = providers.Singleton(
        OllamaAdapter,
        base_url=lambda: config_loader.get_adapter_config("ollama")["base_url"],
    )

    limitless_adapter = providers.Singleton(
        LimitlessAdapter,
        api_key=lambda: config_loader.get_adapter_config("limitless")["api_key"],
        base_url=lambda: config_loader.get_adapter_config("limitless")["base_url"],
    )

    remarkable_adapter = providers.Singleton(
        RemarkableAdapter,
        device_token=lambda: config_loader.get_adapter_config("remarkable")[
            "device_token"
        ],
    )

    handwriting_adapter = providers.Singleton(
        HandwritingAdapter,
    )

    # Services
    remarkable_service = providers.Singleton(
        RemarkableService,
        adapter=remarkable_adapter,
    )

    handwriting_service = providers.Singleton(
        HandwritingRecognitionService,
        adapter=handwriting_adapter,
    )

    # Agent Framework
    agent_registry = providers.Singleton(
        AgentRegistry,
    )

    agent_lifecycle = providers.Singleton(
        AgentLifecycle,
        registry=agent_registry,
    )

    # Agent Factories with automatic dependency injection
    limitless_insight_agent_factory = providers.Factory(
        LimitlessContextualInsightAgent,
        config=lambda: config_loader.get_agent_config("limitless_insight")["config"],
        limitless_adapter=limitless_adapter,
        ollama_adapter=ollama_adapter,
        storage_path=lambda: storage_base_path() / "limitless",
    )

    daily_briefing_agent_factory = providers.Factory(
        DailyBriefingAgent,
        config=lambda: config_loader.get_agent_config("daily_briefing")["config"],
        ollama_adapter=ollama_adapter,
        remarkable_adapter=remarkable_adapter,
        storage_path=lambda: storage_base_path() / "briefings",
    )

    project_tracker_agent_factory = providers.Factory(
        ProactiveProjectTrackerAgent,
        config=lambda: config_loader.get_agent_config("project_tracker")["config"],
        ollama_adapter=ollama_adapter,
        storage_path=lambda: storage_base_path() / "projects",
    )

    control_center_agent_factory = providers.Factory(
        ControlCenterAgent,
        config=lambda: config_loader.get_agent_config("control_center")["config"],
        remarkable_service=remarkable_service,
        handwriting_service=handwriting_service,
        storage_path=lambda: storage_base_path() / "control_center",
    )

    @providers.Singleton
    def agent_factory_registry(self) -> Dict[str, providers.Factory]:
        """Registry of agent factories by class name."""
        return {
            "LimitlessContextualInsightAgent": self.limitless_insight_agent_factory,
            "DailyBriefingAgent": self.daily_briefing_agent_factory,
            "ProactiveProjectTrackerAgent": self.project_tracker_agent_factory,
            "ControlCenterAgent": self.control_center_agent_factory,
        }


# Global container instance
container = AgentContainer()


def setup_agents():
    """Set up all enabled agents using DI."""
    registry = container.agent_registry()
    factory_registry = container.agent_factory_registry()

    # Register agent classes
    for agent_class in [
        LimitlessContextualInsightAgent,
        DailyBriefingAgent,
        ProactiveProjectTrackerAgent,
        ControlCenterAgent,
    ]:
        registry.register_agent_class(agent_class)

    # Create enabled agents
    enabled_agents = config_loader.get_all_enabled_agents()

    for agent_name, agent_config in enabled_agents.items():
        agent_class_name = agent_config["class"]
        factory = factory_registry.get(agent_class_name)

        if factory:
            # Create agent with injected dependencies
            agent = factory()
            registry._agents[agent_name] = agent
        else:
            print(f"Warning: No factory found for agent class {agent_class_name}")
