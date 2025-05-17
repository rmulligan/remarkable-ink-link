"""MCP type definitions for InkLink agents."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class JSONRPCMessage:
    """JSON-RPC message format for MCP."""

    jsonrpc: str = "2.0"
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


@dataclass
class MCPRequest:
    """MCP request message."""

    method: str
    params: Dict[str, Any]
    id: str

    def to_jsonrpc(self) -> JSONRPCMessage:
        """Convert to JSON-RPC message."""
        return JSONRPCMessage(
            jsonrpc="2.0", method=self.method, params=self.params, id=self.id
        )


@dataclass
class MCPResponse:
    """MCP response message."""

    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

    def to_jsonrpc(self) -> JSONRPCMessage:
        """Convert to JSON-RPC message."""
        return JSONRPCMessage(result=self.result, error=self.error, id=self.id)


@dataclass
class MCPMessage:
    """MCP message for inter-agent communication."""

    source: str
    target: str
    capability: str
    data: Dict[str, Any]
    id: Optional[str] = None
