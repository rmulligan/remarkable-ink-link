"""Model Context Protocol (MCP) server implementation for InkLink agents."""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


@dataclass
class JSONRPCMessage:
    """JSON-RPC message format for MCP."""

    jsonrpc: str = "2.0"
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class MCPHandler(Protocol):
    """Protocol for MCP message handlers."""

    async def handle_message(self, message: JSONRPCMessage) -> JSONRPCMessage:
        """Handle an incoming MCP message."""
        ...


class Server:
    """MCP Server implementation for handling agent communications."""

    def __init__(self, name: str):
        """Initialize the MCP server."""
        self.name = name
        self.handlers: Dict[str, Callable] = {}
        self.capabilities: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(f"mcp.server.{name}")
        self._running = False

    def register_handler(self, method: str, handler: Callable) -> None:
        """Register a handler for a specific method."""
        self.handlers[method] = handler
        self.logger.debug(f"Registered handler for method: {method}")

    def register_capability(self, capability: Dict[str, Any]) -> None:
        """Register a capability that this server provides."""
        self.capabilities.append(capability)
        self.logger.debug(f"Registered capability: {capability['name']}")

    async def handle_request(self, message: JSONRPCMessage) -> JSONRPCMessage:
        """Handle an incoming request."""
        if not message.method:
            return JSONRPCMessage(
                id=message.id,
                error={"code": -32600, "message": "Invalid Request: missing method"},
            )

        handler = self.handlers.get(message.method)
        if not handler:
            return JSONRPCMessage(
                id=message.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {message.method}",
                },
            )

        try:
            result = await handler(message.params or {})
            return JSONRPCMessage(id=message.id, result=result)
        except Exception as e:
            self.logger.exception(f"Error handling method {message.method}")
            return JSONRPCMessage(
                id=message.id,
                error={"code": -32603, "message": f"Internal error: {str(e)}"},
            )

    async def start(self) -> None:
        """Start the MCP server."""
        self._running = True
        self.logger.info(f"MCP Server '{self.name}' started")

    async def stop(self) -> None:
        """Stop the MCP server."""
        self._running = False
        self.logger.info(f"MCP Server '{self.name}' stopped")

    def get_capabilities(self) -> List[Dict[str, Any]]:
        """Get the list of capabilities this server provides."""
        return self.capabilities

    async def send_message(self, message: JSONRPCMessage) -> JSONRPCMessage:
        """Send a message to the MCP server (placeholder for actual implementation)."""
        # TODO: Implement actual message sending over MCP protocol
        self.logger.debug(f"Sending message: {message}")
        return JSONRPCMessage(id=message.id, result={"status": "message_sent"})
