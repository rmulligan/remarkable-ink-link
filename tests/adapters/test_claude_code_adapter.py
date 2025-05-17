#!/usr/bin/env python
"""Tests for Claude Code adapter."""

import os
from unittest.mock import MagicMock, call, patch

import pytest

from inklink.adapters.claude_code_adapter import ClaudeCodeAdapter


class TestClaudeCodeAdapter:
    """Test suite for Claude Code adapter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = ClaudeCodeAdapter(
            claude_command="claude",
            model="claude-3-5-sonnet-20241022",
            timeout=30,
            max_tokens=4000,
        )

    @patch("subprocess.run")
    def test_check_claude_availability_success(self, mock_run):
        """Test successful Claude CLI availability check."""
        # Mock successful version check
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Claude CLI v1.0.0"
        mock_run.return_value = mock_result

        result = self.adapter._check_claude_availability()

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["claude", "--version"]

    @patch("subprocess.run")
    def test_check_claude_availability_failure(self, mock_run):
        """Test failed Claude CLI availability check."""
        # Mock failed version check
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Command not found"
        mock_run.return_value = mock_result

        result = self.adapter._check_claude_availability()

        assert result is False

    def test_build_command_basic(self):
        """Test basic command building."""
        cmd_parts, stdin_input = self.adapter._build_command("Test prompt")

        assert cmd_parts == ["claude", "--max-tokens", "4000", "-p", "Test prompt"]
        assert stdin_input is None

    def test_build_command_with_session(self):
        """Test command building with session management."""
        # Test with continue session
        cmd_parts, _ = self.adapter._build_command("Test prompt", continue_session=True)
        assert "-c" in cmd_parts

        # Test with specific session ID
        cmd_parts, _ = self.adapter._build_command(
            "Test prompt", session_id="test-session"
        )
        assert "-r" in cmd_parts
        assert "test-session" in cmd_parts

    def test_build_command_with_piped_input(self):
        """Test command building with piped input."""
        cmd_parts, stdin_input = self.adapter._build_command(
            "Analyze this code", piped_input="def hello(): pass"
        )

        assert stdin_input == "def hello(): pass"

    @patch("subprocess.Popen")
    def test_execute_claude_success(self, mock_popen):
        """Test successful Claude execution."""
        # Mock successful process
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Generated code", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        success, result = self.adapter._execute_claude("Generate Python code")

        assert success is True
        assert result == "Generated code"

    @patch("subprocess.Popen")
    def test_execute_claude_failure(self, mock_popen):
        """Test failed Claude execution."""
        # Mock failed process
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "Error: API limit reached")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        success, result = self.adapter._execute_claude("Generate code")

        assert success is False
        assert "Claude CLI failed" in result

    @patch("subprocess.Popen")
    def test_execute_claude_timeout(self, mock_popen):
        """Test Claude execution timeout."""
        # Mock timeout
        import subprocess

        mock_process = MagicMock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired("cmd", 30)
        mock_popen.return_value = mock_process

        success, result = self.adapter._execute_claude("Generate code")

        assert success is False
        assert "timed out" in result

    @patch.object(ClaudeCodeAdapter, "_execute_claude")
    def test_generate_code_success(self, mock_execute):
        """Test successful code generation."""
        # Mock successful execution with code block
        mock_execute.return_value = (
            True,
            "Here's the code:\n```python\ndef hello():\n    print('Hello')\n```",
        )

        success, code = self.adapter.generate_code(
            "Generate a hello function", language="python"
        )

        assert success is True
        assert code == "def hello():\n    print('Hello')"

    @patch.object(ClaudeCodeAdapter, "_execute_claude")
    def test_generate_code_no_code_block(self, mock_execute):
        """Test code generation without markdown code block."""
        # Mock execution returning plain code
        mock_execute.return_value = (True, "def hello(): pass")

        success, code = self.adapter.generate_code("Generate code")

        assert success is True
        assert code == "def hello(): pass"

    @patch.object(ClaudeCodeAdapter, "_execute_claude")
    def test_review_code_success(self, mock_execute):
        """Test successful code review."""
        # Mock review response
        review_text = """
        Summary: The code is well-structured.
        Issues: No major issues found.
        Improvements: Consider adding type hints.
        Best Practices: Follow PEP 8 style guide.
        """
        mock_execute.return_value = (True, review_text)

        success, feedback = self.adapter.review_code(
            "def hello(): pass", language="python"
        )

        assert success is True
        assert isinstance(feedback, dict)
        assert "summary" in feedback
        assert "issues" in feedback
        assert "improvements" in feedback
        assert "best_practices" in feedback

    @patch.object(ClaudeCodeAdapter, "_execute_claude")
    def test_debug_code_success(self, mock_execute):
        """Test successful code debugging."""
        # Mock debug response with fixed code
        debug_text = """
        The error is caused by undefined variable.
        Here's the fix:
        ```python
        def hello():
            name = "World"
            print(f"Hello {name}")
        ```
        """
        mock_execute.return_value = (True, debug_text)

        success, debug_info = self.adapter.debug_code(
            "def hello(): print(name)", "NameError: name 'name' is not defined"
        )

        assert success is True
        assert isinstance(debug_info, dict)
        assert "fixed_code" in debug_info
        assert (
            debug_info["fixed_code"]
            == 'def hello():\n    name = "World"\n    print(f"Hello {name}")'
        )

    @patch.object(ClaudeCodeAdapter, "_execute_claude")
    def test_ask_best_practices(self, mock_execute):
        """Test best practices query."""
        mock_execute.return_value = (
            True,
            "Use virtual environments for Python projects.",
        )

        success, advice = self.adapter.ask_best_practices(
            "How to manage Python dependencies?", language="python"
        )

        assert success is True
        assert "virtual environments" in advice

    @patch.object(ClaudeCodeAdapter, "_execute_claude")
    def test_summarize_text(self, mock_execute):
        """Test text summarization."""
        mock_execute.return_value = (True, "This code implements a REST API.")

        success, summary = self.adapter.summarize_text(
            "Long technical document...", focus="architecture"
        )

        assert success is True
        assert "REST API" in summary

    @patch.object(ClaudeCodeAdapter, "_execute_claude")
    def test_explain_code(self, mock_execute):
        """Test code explanation."""
        mock_execute.return_value = (True, "This function prints a greeting message.")

        success, explanation = self.adapter.explain_code(
            "def hello(): print('Hello')", language="python", detail_level="simple"
        )

        assert success is True
        assert "greeting" in explanation

    def test_cache_result(self, tmp_path):
        """Test result caching."""
        # Use temporary directory for cache
        adapter = ClaudeCodeAdapter(cache_dir=str(tmp_path))

        # Cache a result
        adapter._cache_result("code_generation", "test_key", "cached_code")

        # Verify cache file was created
        cache_files = list(tmp_path.glob("code_generation_test_key_*.json"))
        assert len(cache_files) == 1

    def test_get_cached_result(self, tmp_path):
        """Test retrieving cached results."""
        adapter = ClaudeCodeAdapter(cache_dir=str(tmp_path))

        # Cache a result
        adapter._cache_result("code_generation", "test_key", "cached_code")

        # Retrieve the cached result
        result = adapter.get_cached_result("code_generation", "test_key", max_age=3600)

        assert result == "cached_code"

    def test_get_cached_result_expired(self, tmp_path):
        """Test retrieving expired cached results."""
        adapter = ClaudeCodeAdapter(cache_dir=str(tmp_path))

        # Cache a result
        adapter._cache_result("code_generation", "test_key", "cached_code")

        # Try to retrieve with max_age=0 (immediately expired)
        result = adapter.get_cached_result("code_generation", "test_key", max_age=0)

        assert result is None

    def test_manage_session(self):
        """Test session management."""
        session_id = "test-session"

        # Create session
        assert self.adapter.manage_session(session_id, "create") is True
        assert session_id in self.adapter.sessions

        # Resume session
        assert self.adapter.manage_session(session_id, "resume") is True
        assert self.adapter.sessions[session_id]["turn_count"] == 1

        # End session
        assert self.adapter.manage_session(session_id, "end") is True
        assert session_id not in self.adapter.sessions

    @patch.object(ClaudeCodeAdapter, "_execute_claude")
    def test_continue_conversation(self, mock_execute):
        """Test conversation continuation."""
        mock_execute.return_value = (True, "Continued response")

        # Create a session first
        self.adapter.manage_session("test-session", "create")

        # Continue conversation
        success, response = self.adapter.continue_conversation(
            "Follow up question", session_id="test-session"
        )

        assert success is True
        assert response == "Continued response"

    def test_create_coding_prompt(self):
        """Test coding prompt creation."""
        prompt = self.adapter.create_coding_prompt(
            "refactor",
            {"quality": "readability", "constraints": "maintain API"},
            style_guide="PEP 8",
        )

        assert "readability" in prompt
        assert "maintain API" in prompt
        assert "PEP 8" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
