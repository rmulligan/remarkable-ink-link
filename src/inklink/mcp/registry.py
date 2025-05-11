"""
MCP tools registry for InkLink.

This module provides a registry for MCP tools and a mechanism
for registering and retrieving tool handlers.
"""

import logging
import importlib
from typing import Dict, Any, Callable, Optional

logger = logging.getLogger(__name__)


class MCPRegistry:
    """
    Registry for MCP tools.

    This class provides functionality to register MCP tool handlers
    and retrieve them by name.
    """

    def __init__(self):
        """Initialize the MCP registry."""
        self.tools: Dict[str, Callable] = {}

    def register_tool(self, tool_name: str, handler: Callable) -> None:
        """
        Register a tool handler.

        Args:
            tool_name: Name of the tool
            handler: Function to handle tool requests
        """
        self.tools[tool_name] = handler
        logger.info(f"Registered MCP tool: {tool_name}")

    def get_tool(self, tool_name: str) -> Optional[Callable]:
        """
        Get a tool handler by name.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool handler function or None if not found
        """
        return self.tools.get(tool_name)

    def register_from_module(self, module_name: str, tool_prefix: str = "") -> None:
        """
        Register all tool handlers from a module.

        Automatically registers any function that starts with the specified
        prefix in the given module.

        Args:
            module_name: Name of the module
            tool_prefix: Prefix for tool functions (optional)
        """
        try:
            module = importlib.import_module(module_name)

            # Get all functions that might be tool handlers
            for name in dir(module):
                if tool_prefix and not name.startswith(tool_prefix):
                    continue

                obj = getattr(module, name)
                if callable(obj):
                    # Register the function
                    tool_name = name
                    if tool_prefix and name.startswith(tool_prefix):
                        # Remove prefix if present
                        tool_name = name[len(tool_prefix) :]

                    self.register_tool(tool_name, obj)

            logger.info(f"Registered tools from module {module_name}")
        except ImportError as e:
            logger.error(f"Failed to import module {module_name}: {e}")
        except Exception as e:
            logger.error(f"Error registering tools from module {module_name}: {e}")

    def handle_tool_request(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle an MCP tool request.

        Args:
            tool_name: Name of the tool
            params: Parameters for the tool

        Returns:
            Result from the tool handler or error response
        """
        handler = self.get_tool(tool_name)

        if not handler:
            logger.error(f"No handler found for MCP tool: {tool_name}")
            return {"success": False, "error": f"Tool not found: {tool_name}"}

        try:
            # Call the handler with parameters
            result = handler(params)
            return result
        except Exception as e:
            logger.error(f"Error handling tool request {tool_name}: {e}")
            return {"success": False, "error": str(e)}


# Create a singleton instance
registry = MCPRegistry()


def register_all_tools():
    """Register all MCP tools in the project."""
    # Register knowledge graph tools
    registry.register_from_module("inklink.mcp.knowledge_graph_tools_integration")

    # Other tool modules can be registered here
    # registry.register_from_module("inklink.mcp.other_tools")


def get_registry() -> MCPRegistry:
    """
    Get the MCP registry instance.

    Returns:
        Singleton registry instance
    """
    return registry
