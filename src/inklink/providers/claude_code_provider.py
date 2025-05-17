#!/usr/bin/env python
"""
Claude Code LLM Provider implementation.

This module provides an implementation of the LLM interfaces using
the Claude Code adapter.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from inklink.adapters.claude_code_adapter import ClaudeCodeAdapter
from inklink.services.llm_interface import ITechnicalLLMProvider


class ClaudeCodeProvider(ITechnicalLLMProvider):
    """
    Claude Code implementation of the technical LLM provider interface.

    This provider uses Claude Code for code generation, review, debugging,
    and technical documentation tasks.
    """

    def __init__(
        self,
        adapter: Optional[ClaudeCodeAdapter] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the Claude Code provider.

        Args:
            adapter: Optional Claude Code adapter instance
            config: Optional configuration dictionary
        """
        self.logger = logging.getLogger(__name__)

        # Use provided adapter or create new one
        if adapter:
            self.adapter = adapter
        else:
            # Get config from provided dict or environment
            config = config or {}
            self.adapter = ClaudeCodeAdapter(
                claude_command=config.get("CLAUDE_CODE_COMMAND"),
                model=config.get("CLAUDE_CODE_MODEL"),
                timeout=config.get("CLAUDE_CODE_TIMEOUT", 120),
                max_tokens=config.get("CLAUDE_CODE_MAX_TOKENS", 8000),
                temperature=config.get("CLAUDE_CODE_TEMPERATURE", 0.7),
                cache_dir=config.get("CLAUDE_CODE_CACHE_DIR"),
            )

    def is_available(self) -> bool:
        """Check if Claude Code is available."""
        return self.adapter.is_available()

    def ask(self, prompt: str, context: Optional[str] = None) -> Tuple[bool, str]:
        """
        Ask a general question to Claude Code.

        Args:
            prompt: The question or prompt
            context: Optional context for the question

        Returns:
            Tuple of (success, response)
        """
        try:
            # For general questions, use Claude's general capabilities
            full_prompt = prompt
            if context:
                full_prompt = f"Context: {context}\n\nQuestion: {prompt}"

            success, result = self.adapter._execute_claude(full_prompt)
            return success, result

        except Exception as e:
            self.logger.error(f"Error in ask: {e}")
            return False, str(e)

    def generate_code(
        self,
        prompt: str,
        language: Optional[str] = None,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        Generate code based on a prompt.

        Args:
            prompt: The code generation prompt
            language: Target programming language
            context: Additional context (e.g., existing code)
            session_id: Optional session ID for context

        Returns:
            Tuple of (success, generated_code_or_error)
        """
        return self.adapter.generate_code(prompt, language, context, session_id)

    def review_code(
        self,
        code: str,
        language: Optional[str] = None,
        instruction: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        Review code and provide feedback.

        Args:
            code: The code to review
            language: Programming language of the code
            instruction: Specific review instructions
            session_id: Optional session ID for context

        Returns:
            Tuple of (success, review_feedback_or_error)
        """
        return self.adapter.review_code(code, language, instruction, session_id)

    def debug_code(
        self,
        code: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        Debug code and suggest fixes for errors.

        Args:
            code: The code with errors
            error_message: The error message
            stack_trace: Optional stack trace
            session_id: Optional session ID for context

        Returns:
            Tuple of (success, debug_suggestions_or_error)
        """
        return self.adapter.debug_code(code, error_message, stack_trace, session_id)

    def explain_code(
        self,
        code: str,
        language: Optional[str] = None,
        detail_level: str = "medium",
        session_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Explain what a piece of code does.

        Args:
            code: The code to explain
            language: Programming language
            detail_level: Level of detail ("simple", "medium", "detailed")
            session_id: Optional session ID for context

        Returns:
            Tuple of (success, explanation)
        """
        return self.adapter.explain_code(code, language, detail_level, session_id)

    def ask_best_practices(
        self,
        query: str,
        language: Optional[str] = None,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Ask for best practices or technical guidance.

        Args:
            query: The technical question
            language: Optional programming language context
            context: Additional context
            session_id: Optional session ID for context

        Returns:
            Tuple of (success, best_practices_advice)
        """
        return self.adapter.ask_best_practices(query, language, context, session_id)

    def summarize_text(
        self,
        text: str,
        focus: Optional[str] = None,
        max_length: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Summarize technical text or documentation.

        Args:
            text: The text to summarize
            focus: Optional focus area for summarization
            max_length: Optional maximum length for summary
            session_id: Optional session ID for context

        Returns:
            Tuple of (success, summary)
        """
        return self.adapter.summarize_text(text, focus, max_length, session_id)

    def create_session(self, session_id: str) -> bool:
        """
        Create a new session for multi-turn conversations.

        Args:
            session_id: Unique session identifier

        Returns:
            Success status
        """
        return self.adapter.manage_session(session_id, "create")

    def end_session(self, session_id: str) -> bool:
        """
        End an existing session.

        Args:
            session_id: Session identifier to end

        Returns:
            Success status
        """
        return self.adapter.manage_session(session_id, "end")

    def continue_conversation(
        self, prompt: str, session_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Continue a conversation with Claude using session management.

        Args:
            prompt: The continuation prompt
            session_id: Optional session ID (uses last session if None)

        Returns:
            Tuple of (success, response)
        """
        return self.adapter.continue_conversation(prompt, session_id)

    def get_cached_result(
        self, operation: str, key: str, max_age: int = 3600
    ) -> Optional[Any]:
        """
        Retrieve a cached result if available.

        Args:
            operation: Type of operation
            key: Cache key
            max_age: Maximum age in seconds

        Returns:
            Cached result or None
        """
        return self.adapter.get_cached_result(operation, key, max_age)

    def __repr__(self):
        """String representation of the provider."""
        return f"ClaudeCodeProvider(available={self.is_available()})"
