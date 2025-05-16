"""Agent registry for managing and discovering agents."""

import asyncio
import logging
from typing import Dict, List, Optional, Type

from .agent import AgentConfig, AgentState, LocalAgent


class AgentRegistry:
    """Registry for managing local agents."""

    def __init__(self):
        """Initialize the registry."""
        self.logger = logging.getLogger("agent.registry")
        self._agents: Dict[str, LocalAgent] = {}
        self._agent_classes: Dict[str, Type[LocalAgent]] = {}
        self._lock = asyncio.Lock()

    def register_agent_class(self, agent_class: Type[LocalAgent]) -> None:
        """Register an agent class for later instantiation."""
        if not issubclass(agent_class, LocalAgent):
            raise ValueError(f"{agent_class} must be a subclass of LocalAgent")

        # Use the class name as identifier
        class_name = agent_class.__name__
        self._agent_classes[class_name] = agent_class
        self.logger.info(f"Registered agent class: {class_name}")

    async def create_agent(self, class_name: str, config: "AgentConfig") -> LocalAgent:
        """Create and register an agent instance."""
        async with self._lock:
            if config.name in self._agents:
                raise ValueError(f"Agent with name '{config.name}' already exists")

            if class_name not in self._agent_classes:
                raise ValueError(f"Unknown agent class: {class_name}")

            agent_class = self._agent_classes[class_name]
            agent = agent_class(config)
            self._agents[config.name] = agent
            self.logger.info(f"Created agent '{config.name}' of type {class_name}")
            return agent

    async def get_agent(self, name: str) -> Optional[LocalAgent]:
        """Get an agent by name."""
        return self._agents.get(name)

    async def list_agents(self) -> List[LocalAgent]:
        """List all registered agents."""
        return list(self._agents.values())

    async def list_running_agents(self) -> List[LocalAgent]:
        """List all running agents."""
        return [
            agent
            for agent in self._agents.values()
            if agent.get_state() == AgentState.RUNNING
        ]

    async def start_agent(self, name: str) -> None:
        """Start a specific agent."""
        agent = await self.get_agent(name)
        if not agent:
            raise ValueError(f"Agent '{name}' not found")

        await agent.start()

    async def stop_agent(self, name: str) -> None:
        """Stop a specific agent."""
        agent = await self.get_agent(name)
        if not agent:
            raise ValueError(f"Agent '{name}' not found")

        await agent.stop()

    async def start_all(self) -> None:
        """Start all registered agents."""
        self.logger.info("Starting all agents")
        tasks = []
        for agent in self._agents.values():
            if agent.get_state() == AgentState.INITIALIZED:
                tasks.append(agent.start())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def stop_all(self) -> None:
        """Stop all running agents."""
        self.logger.info("Stopping all agents")
        tasks = []
        for agent in self._agents.values():
            if agent.get_state() == AgentState.RUNNING:
                tasks.append(agent.stop())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def remove_agent(self, name: str) -> None:
        """Remove an agent from the registry."""
        async with self._lock:
            agent = self._agents.get(name)
            if not agent:
                raise ValueError(f"Agent '{name}' not found")

            # Stop the agent if it's running
            if agent.get_state() == AgentState.RUNNING:
                await agent.stop()

            del self._agents[name]
            self.logger.info(f"Removed agent '{name}'")

    def get_registered_classes(self) -> List[str]:
        """Get list of registered agent class names."""
        return list(self._agent_classes.keys())

    def __repr__(self) -> str:
        """String representation of the registry."""
        agent_count = len(self._agents)
        running_count = len(
            [a for a in self._agents.values() if a.get_state() == AgentState.RUNNING]
        )
        return f"<AgentRegistry agents={agent_count} running={running_count}>"
