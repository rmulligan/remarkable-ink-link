"""MCP integration for LocalAgent framework."""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Dict, List, Optional

from inklink.mcp.server import JSONRPCMessage as MCP_JSONRPCMessage
from inklink.mcp.server import Server as MCPServer

from .agent import AgentConfig, LocalAgent


@dataclass
class MCPCapability:
    """Definition of an MCP capability."""

    name: str
    description: str
    handler: Callable[[Dict[str, Any]], Coroutine[Any, Any, Dict[str, Any]]]
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None


class MCPAgentMixin:
    """Mixin to add MCP capabilities to LocalAgent."""

    def __init__(self, *args, **kwargs):
        """Initialize MCP mixin."""
        super().__init__(*args, **kwargs)
        self._mcp_capabilities: Dict[str, MCPCapability] = {}
        self._mcp_server: Optional[MCPServer] = None
        self._mcp_logger = logging.getLogger(f"agent.{self.config.name}.mcp")

    def register_mcp_capability(self, capability: MCPCapability) -> None:
        """Register an MCP capability."""
        self._mcp_capabilities[capability.name] = capability
        self._mcp_logger.info(f"Registered MCP capability: {capability.name}")

    async def _initialize_mcp(self) -> None:
        """Initialize MCP server for the agent."""
        if not self.config.mcp_enabled:
            return

        self._mcp_logger.info("Initializing MCP server")

        # Create MCP server configuration
        # Note: Configuration is now handled internally by the server

        # Initialize the MCP server
        self._mcp_server = MCPServer(f"agent_{self.config.name}")

        # Register capability handlers
        for name, capability in self._mcp_capabilities.items():
            self._mcp_server.register_handler(
                name, self._create_mcp_handler(capability)
            )

        # Start the MCP server
        await self._mcp_server.start()
        self._mcp_logger.info("MCP server started successfully")

    async def _cleanup_mcp(self) -> None:
        """Clean up MCP server resources."""
        if self._mcp_server:
            self._mcp_logger.info("Stopping MCP server")
            await self._mcp_server.stop()
            self._mcp_server = None

    def _create_mcp_handler(self, capability: MCPCapability) -> Callable:
        """Create an MCP message handler for a capability."""

        async def handler(data: Dict[str, Any]) -> Dict[str, Any]:
            try:
                # Call the capability handler with the data
                result = await capability.handler(data)
                return result
            except Exception as e:
                self._mcp_logger.error(
                    f"Error handling MCP message for {capability.name}: {e}"
                )
                return {"error": str(e)}

        return handler

    async def send_mcp_message(
        self, target: str, capability: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send an MCP message to another agent."""
        if not self._mcp_server:
            raise RuntimeError("MCP server not initialized")

        # Create a JSON-RPC message for MCP communication
        jsonrpc_message = MCP_JSONRPCMessage(
            method=f"{target}.{capability}",
            params=data,
            id=f"{self.config.name}_{target}_{capability}_{id(data)}",
        )

        response = await self._mcp_server.send_message(jsonrpc_message)
        return response.result or {"error": response.error}

    def get_mcp_capabilities(self) -> List[str]:
        """Get list of MCP capabilities."""
        return list(self._mcp_capabilities.keys())


class MCPEnabledAgent(MCPAgentMixin, LocalAgent):
    """LocalAgent with MCP capabilities."""

    def __init__(self, config: "AgentConfig"):
        """Initialize MCP-enabled agent."""
        super().__init__(config)
        self._setup_default_capabilities()

    def _setup_default_capabilities(self) -> None:
        """Set up default MCP capabilities."""
        # Register health check capability
        self.register_mcp_capability(
            MCPCapability(
                name="health_check",
                description="Check agent health status",
                handler=self._handle_health_check,
            )
        )

        # Register status capability
        self.register_mcp_capability(
            MCPCapability(
                name="get_status",
                description="Get agent status information",
                handler=self._handle_get_status,
            )
        )

    async def _handle_health_check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check requests."""
        return {
            "status": "healthy",
            "state": self.state.value,
            "agent": self.config.name,
        }

    async def _handle_get_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status requests."""
        return {
            "name": self.config.name,
            "version": self.config.version,
            "state": self.state.value,
            "capabilities": self.config.capabilities,
            "mcp_capabilities": self.get_mcp_capabilities(),
        }
