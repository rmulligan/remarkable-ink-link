"""
MCP Controller for handling Model Context Protocol tool requests.

This controller provides endpoints for invoking MCP tools registered
in the application's tool registry.
"""

import json
import logging
from typing import Any, Dict

from inklink.controllers.base_controller import BaseController
from inklink.mcp.registry import get_registry, register_all_tools

logger = logging.getLogger(__name__)


class MCPController(BaseController):
    """
    Controller for MCP-related endpoints.

    This controller handles:
    - Listing available MCP tools
    - Invoking MCP tools with parameters
    - Providing tool metadata
    """

    def __init__(self):
        """Initialize the MCPController."""
        super().__init__()
        # Register all MCP tools
        register_all_tools()
        self.registry = get_registry()
        self._register_routes()

    def _register_routes(self):
        """Register routes for this controller."""
        # Tools listing and metadata
        self.add_route("GET", "/mcp/tools", self.list_tools)
        self.add_route("GET", "/mcp/tools/({tool_name})", self.get_tool_info)

        # Tool invocation
        self.add_route("POST", "/mcp/tools/({tool_name})", self.invoke_tool)

    async def list_tools(self, request):
        """
        List all available MCP tools.

        Returns:
            HTTP response with list of tools
        """
        tools = list(self.registry.tools.keys())

        return self.json_response({"tools": tools, "count": len(tools)})

    async def get_tool_info(self, request):
        """
        Get information about a specific MCP tool.

        Returns:
            HTTP response with tool information
        """
        tool_name = request.match_info.get("tool_name")

        handler = self.registry.get_tool(tool_name)
        if not handler:
            return self.error_response(f"Tool not found: {tool_name}", 404)

        # Get function docstring and signature
        docstring = handler.__doc__ or "No documentation available"

        return self.json_response(
            {"name": tool_name, "description": docstring, "available": True}
        )

    async def invoke_tool(self, request):
        """
        Invoke an MCP tool with parameters.

        Returns:
            HTTP response with tool result
        """
        tool_name = request.match_info.get("tool_name")

        try:
            params = await request.json()
        except json.JSONDecodeError:
            return self.error_response("Invalid JSON in request body", 400)

        handler = self.registry.get_tool(tool_name)
        if not handler:
            return self.error_response(f"Tool not found: {tool_name}", 404)

        try:
            # Execute the tool
            result = self.registry.handle_tool_request(tool_name, params)
            return self.json_response(result)
        except Exception as e:
            logger.error(f"Error invoking MCP tool {tool_name}: {e}")
            return self.error_response(f"Error invoking tool: {str(e)}", 500)
