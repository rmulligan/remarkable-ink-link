"""Base LocalAgent class for the InkLink AI Agent Framework."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Coroutine, Dict, List, Optional

from mcp import MCPServer


class AgentState(Enum):
    """Agent state enumeration."""

    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class AgentConfig:
    """Configuration for LocalAgent."""

    name: str
    description: str
    version: str
    capabilities: List[str]
    ollama_model: Optional[str] = None
    mcp_enabled: bool = True
    retry_attempts: int = 3
    timeout_seconds: int = 30


class LocalAgent(ABC):
    """Base class for all local AI agents."""

    def __init__(self, config: AgentConfig):
        """Initialize the agent with configuration."""
        self.config = config
        self.logger = logging.getLogger(f"agent.{config.name}")
        self.state = AgentState.INITIALIZED
        self._mcp_server: Optional[MCPServer] = None
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    @abstractmethod
    async def _agent_logic(self) -> None:
        """Main agent logic - implemented by subclasses."""

    @abstractmethod
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests - implemented by subclasses."""

    async def start(self) -> None:
        """Start the agent."""
        if self.state != AgentState.INITIALIZED:
            raise RuntimeError(
                f"Agent {self.config.name} cannot start from state {self.state}"
            )

        self.state = AgentState.STARTING
        self.logger.info(f"Starting agent {self.config.name}")

        try:
            # Initialize MCP server if enabled
            if self.config.mcp_enabled:
                await self._initialize_mcp()

            # Start the main agent loop
            self._task = asyncio.create_task(self._run())
            self.state = AgentState.RUNNING
            self.logger.info(f"Agent {self.config.name} started successfully")

        except Exception as e:
            self.state = AgentState.ERROR
            self.logger.error(f"Failed to start agent {self.config.name}: {e}")
            raise

    async def stop(self) -> None:
        """Stop the agent gracefully."""
        if self.state != AgentState.RUNNING:
            self.logger.warning(f"Agent {self.config.name} not running, cannot stop")
            return

        self.state = AgentState.STOPPING
        self.logger.info(f"Stopping agent {self.config.name}")

        # Signal the agent to stop
        self._stop_event.set()

        # Wait for the task to complete
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                self.logger.warning(
                    f"Agent {self.config.name} did not stop gracefully, cancelling"
                )
                self._task.cancel()

        # Cleanup MCP server
        if self._mcp_server:
            await self._cleanup_mcp()

        self.state = AgentState.STOPPED
        self.logger.info(f"Agent {self.config.name} stopped")

    async def _run(self) -> None:
        """Main agent run loop."""
        try:
            while not self._stop_event.is_set():
                await self._agent_logic()
                # Small delay to prevent tight loops
                await asyncio.sleep(0.1)
        except Exception as e:
            self.state = AgentState.ERROR
            self.logger.error(f"Agent {self.config.name} encountered error: {e}")
            raise

    async def _initialize_mcp(self) -> None:
        """Initialize MCP server for the agent."""

    async def _cleanup_mcp(self) -> None:
        """Clean up MCP server resources."""

    def get_state(self) -> AgentState:
        """Get current agent state."""
        return self.state

    def get_capabilities(self) -> List[str]:
        """Get agent capabilities."""
        return self.config.capabilities

    def __repr__(self) -> str:
        """String representation of the agent."""
        return (
            f"<{self.__class__.__name__} '{self.config.name}' state={self.state.value}>"
        )
