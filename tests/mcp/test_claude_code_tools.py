#!/usr/bin/env python
"""
Tests for Claude Code MCP tools.

This module tests the MCP tool implementations for Claude Code integration.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from inklink.mcp.claude_code_tools import (
    claude_code_best_practices,
    claude_code_debug,
    claude_code_generate,
    claude_code_manage_session,
    claude_code_review,
    claude_code_summarize,
    register_claude_code_tools,
)


class TestClaudeCodeMCPTools:
    """Test suite for Claude Code MCP tools."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Mock the LLMServiceManager
        self.mock_service_manager = Mock()
        self.mock_llm_interface = Mock()
        self.mock_claude_provider = Mock()

        # Set up return values
        self.mock_service_manager.get_llm_interface.return_value = (
            self.mock_llm_interface
        )
        self.mock_service_manager.get_llm_provider.return_value = (
            self.mock_claude_provider
        )

        # Set up routing response
        self.mock_routing = {
            "provider": "claude_code",
            "privacy_level": "public",
            "complexity": 0.8,
            "routing_path": ["claude_code", "local_llm"],
            "reasoning": "Routed to Claude Code for high complexity task.",
        }
        self.mock_service_manager.route_task.return_value = self.mock_routing

        # Set up LLM interface response
        self.mock_result = {
            "success": True,
            "result": "Generated code or response",
            "session_id": "test-session-id",
        }
        self.mock_llm_interface.route_request.return_value = self.mock_result

    @patch("inklink.mcp.claude_code_tools.LLMServiceManager")
    def test_claude_code_generate(self, mock_manager_class):
        """Test code generation MCP tool."""
        mock_manager_class.return_value = self.mock_service_manager

        params = {
            "prompt": "Create a Python function to calculate factorial",
            "language": "python",
            "context": "Use recursion",
        }

        result = claude_code_generate(params)

        # Verify the result
        assert result["success"] is True
        assert result["code"] == "Generated code or response"
        assert result["provider"] == "claude_code"
        assert result["language"] == "python"
        assert "routing" in result

        # Verify service manager was called correctly
        self.mock_service_manager.route_task.assert_called_once_with(
            "code_generation", params["prompt"]
        )

        # Verify LLM interface was called
        self.mock_llm_interface.route_request.assert_called_once()

    @patch("inklink.mcp.claude_code_tools.LLMServiceManager")
    def test_claude_code_generate_no_prompt(self, mock_manager_class):
        """Test code generation with missing prompt."""
        result = claude_code_generate({})

        assert result["success"] is False
        assert result["error"] == "No prompt provided"

    @patch("inklink.mcp.claude_code_tools.LLMServiceManager")
    def test_claude_code_review(self, mock_manager_class):
        """Test code review MCP tool."""
        mock_manager_class.return_value = self.mock_service_manager

        # Update mock result for code review
        self.mock_result["issues"] = ["Issue 1", "Issue 2"]
        self.mock_result["improvements"] = ["Improvement 1"]

        params = {
            "code": "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
            "language": "python",
            "focus_areas": ["performance", "readability"],
        }

        result = claude_code_review(params)

        # Verify the result
        assert result["success"] is True
        assert result["review"] == "Generated code or response"
        assert result["issues"] == ["Issue 1", "Issue 2"]
        assert result["improvements"] == ["Improvement 1"]
        assert result["provider"] == "claude_code"

        # Verify routing
        self.mock_service_manager.route_task.assert_called_once_with(
            "code_review", params["code"]
        )

    @patch("inklink.mcp.claude_code_tools.LLMServiceManager")
    def test_claude_code_debug(self, mock_manager_class):
        """Test code debugging MCP tool."""
        mock_manager_class.return_value = self.mock_service_manager

        # Update mock result for debugging
        self.mock_result["fixes"] = ["Fix 1", "Fix 2"]
        self.mock_result["explanation"] = "The issue is..."
        self.mock_result["fixed_code"] = "def fixed_function()..."

        params = {
            "code": "def buggy_function(): return 1/0",
            "error_message": "ZeroDivisionError",
            "expected_behavior": "Return a valid number",
            "language": "python",
        }

        result = claude_code_debug(params)

        # Verify the result
        assert result["success"] is True
        assert result["analysis"] == "Generated code or response"
        assert result["fixes"] == ["Fix 1", "Fix 2"]
        assert result["explanation"] == "The issue is..."
        assert result["fixed_code"] == "def fixed_function()..."

        # Verify routing
        self.mock_service_manager.route_task.assert_called_once_with(
            "debugging", params["code"]
        )

    @patch("inklink.mcp.claude_code_tools.LLMServiceManager")
    def test_claude_code_best_practices(self, mock_manager_class):
        """Test best practices MCP tool."""
        mock_manager_class.return_value = self.mock_service_manager

        # Update mock result for best practices
        self.mock_result["examples"] = ["Example 1", "Example 2"]
        self.mock_result["resources"] = ["Resource 1", "Resource 2"]

        params = {
            "topic": "Python async/await patterns",
            "language": "python",
            "level": "intermediate",
        }

        result = claude_code_best_practices(params)

        # Verify the result
        assert result["success"] is True
        assert result["best_practices"] == "Generated code or response"
        assert result["examples"] == ["Example 1", "Example 2"]
        assert result["resources"] == ["Resource 1", "Resource 2"]

        # Verify routing
        self.mock_service_manager.route_task.assert_called_once_with(
            "best_practices", params["topic"]
        )

    @patch("inklink.mcp.claude_code_tools.LLMServiceManager")
    def test_claude_code_summarize(self, mock_manager_class):
        """Test technical summarization MCP tool."""
        mock_manager_class.return_value = self.mock_service_manager

        # Update mock result for summarization
        self.mock_result["key_points"] = ["Point 1", "Point 2"]
        self.mock_result["technical_details"] = {"detail1": "value1"}

        params = {
            "content": "Long technical documentation...",
            "type": "docs",
            "style": "brief",
        }

        result = claude_code_summarize(params)

        # Verify the result
        assert result["success"] is True
        assert result["summary"] == "Generated code or response"
        assert result["key_points"] == ["Point 1", "Point 2"]
        assert result["technical_details"] == {"detail1": "value1"}

        # Verify routing
        self.mock_service_manager.route_task.assert_called_once_with(
            "technical_summary", params["content"]
        )

    @patch("inklink.mcp.claude_code_tools.LLMServiceManager")
    def test_claude_code_manage_session(self, mock_manager_class):
        """Test session management MCP tool."""
        mock_manager_class.return_value = self.mock_service_manager

        # Set up session management response
        self.mock_claude_provider.create_session.return_value = {
            "session_id": "new-session-id",
            "status": "active",
            "context_size": 0,
        }

        params = {
            "action": "create",
            "metadata": {"user": "test-user"},
        }

        result = claude_code_manage_session(params)

        # Verify the result
        assert result["success"] is True
        assert result["action"] == "create"
        assert result["session_id"] == "new-session-id"
        assert result["status"] == "active"

        # Verify Claude provider was called
        self.mock_claude_provider.create_session.assert_called_once_with(
            metadata={"user": "test-user"}
        )

    @patch("inklink.mcp.claude_code_tools.LLMServiceManager")
    def test_claude_code_manage_session_no_provider(self, mock_manager_class):
        """Test session management when Claude provider is not available."""
        mock_manager_class.return_value = self.mock_service_manager
        self.mock_service_manager.get_llm_provider.return_value = None

        params = {"action": "create"}

        result = claude_code_manage_session(params)

        assert result["success"] is False
        assert result["error"] == "Claude Code provider not available"

    @patch("inklink.mcp.claude_code_tools.LLMServiceManager")
    def test_error_handling(self, mock_manager_class):
        """Test error handling in MCP tools."""
        # Make the service manager raise an exception
        mock_manager_class.side_effect = Exception("Test error")

        params = {"prompt": "Test prompt"}

        result = claude_code_generate(params)

        assert result["success"] is False
        assert result["error"] == "Test error"

    def test_register_claude_code_tools(self):
        """Test registering Claude Code tools with MCP registry."""
        mock_registry = Mock()

        register_claude_code_tools(mock_registry)

        # Verify all tools were registered
        expected_tools = [
            "claude_code_generate",
            "claude_code_review",
            "claude_code_debug",
            "claude_code_best_practices",
            "claude_code_summarize",
            "claude_code_manage_session",
        ]

        for tool_name in expected_tools:
            mock_registry.register_tool.assert_any_call(tool_name, eval(tool_name))

        # Verify correct number of registrations
        assert mock_registry.register_tool.call_count == 6

    @patch("inklink.mcp.claude_code_tools.LLMServiceManager")
    def test_no_available_provider(self, mock_manager_class):
        """Test handling when no provider is available."""
        mock_manager_class.return_value = self.mock_service_manager

        # Set up routing to return no provider
        self.mock_service_manager.route_task.return_value = {
            "provider": None,
            "error": "No available provider",
        }

        params = {"prompt": "Test prompt"}

        result = claude_code_generate(params)

        assert result["success"] is False
        assert result["error"] == "No available provider for code generation"
        assert result["routing"] == {
            "provider": None,
            "error": "No available provider",
        }
