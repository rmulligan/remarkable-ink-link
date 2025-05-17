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

    async def register_agent(self, agent: LocalAgent) -> None:
        """Register an existing agent instance."""
        async with self._lock:
            if agent.config.name in self._agents:
                raise ValueError(
                    f"Agent with name '{agent.config.name}' already registered"
                )

            self._agents[agent.config.name] = agent
            self.logger.info(f"Registered agent: {agent.config.name}")

    async def unregister_agent(self, agent_name: str) -> Optional[LocalAgent]:
        """Unregister an agent."""
        async with self._lock:
            agent = self._agents.pop(agent_name, None)
            if agent:
                self.logger.info(f"Unregistered agent: {agent_name}")
            return agent

    def get_agent(self, agent_name: str) -> Optional[LocalAgent]:
        """Get an agent by name."""
        return self._agents.get(agent_name)

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self._agents.keys())

    def list_agent_classes(self) -> List[str]:
        """List all registered agent class names."""
        return list(self._agent_classes.keys())

    async def start_agent(self, agent_name: str) -> None:
        """Start a specific agent."""
        agent = self.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not found")

        await agent.start()

    async def stop_agent(self, agent_name: str) -> None:
        """Stop a specific agent."""
        agent = self.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not found")

        await agent.stop()

    async def start_all(self) -> None:
        """Start all registered agents."""
        tasks = []
        for agent_name, agent in self._agents.items():
            self.logger.info(f"Starting agent: {agent_name}")
            tasks.append(agent.start())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def stop_all(self) -> None:
        """Stop all registered agents."""
        tasks = []
        for agent_name, agent in self._agents.items():
            self.logger.info(f"Stopping agent: {agent_name}")
            tasks.append(agent.stop())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def check_agent_health(self, agent_name: str) -> Dict[str, any]:
        """Check health of a specific agent."""
        agent = self.get_agent(agent_name)
        if not agent:
            return {
                "status": "not_found",
                "message": f"Agent '{agent_name}' not found",
            }

        # Basic health check - can be extended
        return {
            "status": "healthy" if agent.state == AgentState.RUNNING else "unhealthy",
            "state": agent.state.value,
            "name": agent.config.name,
            "capabilities": agent.config.capabilities,
        }

    async def check_all_health(self) -> Dict[str, Dict[str, any]]:
        """Check health of all registered agents."""
        health_reports = {}
        for agent_name in self._agents:
            health_reports[agent_name] = await self.check_agent_health(agent_name)
        return health_reports

    def get_agents_by_capability(self, capability: str) -> List[LocalAgent]:
        """Get all agents with a specific capability."""
        matching_agents = []
        for agent in self._agents.values():
            if capability in agent.config.capabilities:
                matching_agents.append(agent)
        return matching_agents

    def get_agent_status(self, agent_name: str) -> Optional[Dict[str, any]]:
        """Get status information for an agent."""
        agent = self.get_agent(agent_name)
        if not agent:
            return None

        return {
            "name": agent.config.name,
            "state": agent.state.value,
            "capabilities": agent.config.capabilities,
            "version": agent.config.version,
            "description": agent.config.description,
        }

    def get_all_status(self) -> Dict[str, Dict[str, any]]:
        """Get status information for all agents."""
        return {
            agent_name: self.get_agent_status(agent_name)
            for agent_name in self._agents
            if self.get_agent_status(agent_name) is not None
        }

    async def discover_agents(self) -> Dict[str, List[str]]:
        """Discover agents by their capabilities."""
        capability_map: Dict[str, List[str]] = {}

        for agent in self._agents.values():
            for capability in agent.config.capabilities:
                if capability not in capability_map:
                    capability_map[capability] = []
                capability_map[capability].append(agent.config.name)

        return capability_map

    async def cleanup(self) -> None:
        """Clean up all resources."""
        await self.stop_all()
        self._agents.clear()
        self._agent_classes.clear()
        self.logger.info("Registry cleaned up")
