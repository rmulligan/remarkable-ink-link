"""AI Service for interacting with Claude via CLI."""

import logging
from typing import Any, Dict, List, Optional, Union

from inklink.adapters.claude_cli_adapter import ClaudeCliAdapter
from inklink.config import CONFIG
from inklink.services.interfaces import IAIService

logger = logging.getLogger(__name__)


class AIService(IAIService):
    """Service for AI text processing using Claude CLI."""

    def __init__(
        self,
        claude_command: Optional[str] = None,
        model: Optional[str] = None,
        adapter: Optional[ClaudeCliAdapter] = None,
    ):
        """
        Initialize AIService with Claude CLI configuration.

        Args:
            claude_command: Command to invoke Claude CLI
            model: Claude model name
            adapter: Optional pre-configured ClaudeCliAdapter
        """
        # Use provided adapter or create a new one
        self.adapter = adapter or ClaudeCliAdapter(
            claude_command=claude_command or CONFIG.get("CLAUDE_COMMAND"),
            model=model or CONFIG.get("CLAUDE_MODEL"),
            system_prompt=CONFIG.get(
                "CLAUDE_SYSTEM_PROMPT", "You are a helpful assistant."
            ),
        )

    def ask(self, prompt: str) -> str:
        """
        Ask a prompt to Claude and return the response text.
        Simplified interface for quick queries.

        Args:
            prompt: The user prompt to send to Claude.

        Returns:
            The Claude-generated response string.
        """
        success, response, _ = self.adapter.process_with_context(
            prompt=prompt,
            new_conversation=True,  # Use a new conversation for each query
        )

        if not success:
            logger.error(f"Claude query failed: {response}")
            return ""
        return response

    def process_query(
        self,
        query_text: str,
        context: Optional[Dict[str, Any]] = None,
        structured_content: Optional[
            Union[List[Dict[str, Any]], Dict[str, Any]]
        ] = None,
        context_window: Optional[int] = None,
        selected_pages: Optional[List[Union[int, str]]] = None,
    ) -> str:
        """
        Process a text query and return a Claude response with document context.

        Parameters:
            query_text (str): The user's query.
            context (dict, optional): Additional context as a dictionary.
            structured_content (list[dict] or dict, optional): Structured document content.
            context_window (int, optional): Number of most recent pages to include.
            selected_pages (list[int] or list[str], optional): Specific pages to include.

        Returns:
            str: Claude-generated response.
        """
        success, response = self.adapter.generate_structured_completion(
            query_text=query_text,
            context=context,
            structured_content=structured_content,
            context_window=context_window,
            selected_pages=selected_pages,
        )

        if not success:
            logger.error(f"Claude structured query failed: {response}")
            return ""
        return response
