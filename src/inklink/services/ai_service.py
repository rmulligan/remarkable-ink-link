"""AI Service for interacting with AI models."""

import logging
from typing import Any, Dict, List, Optional, Union

from inklink.adapters.ai_adapter import AIAdapter
from inklink.config import CONFIG
from inklink.services.interfaces import IAIService

logger = logging.getLogger(__name__)


class AIService(IAIService):
    """Service for AI text processing using various providers."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider: str = "openai",
        ai_adapter: Optional[AIAdapter] = None,
    ):
        """
        Initialize AIService with AI provider configuration.

        Args:
            api_key: API key for the AI provider (optional if using adapter)
            model: AI model name (e.g., 'gpt-3.5-turbo')
            provider: AI provider name ('openai', 'anthropic', etc.)
            ai_adapter: Optional pre-configured AIAdapter
        """
        self.provider = provider or CONFIG.get("AI_PROVIDER", "openai")

        # Use provided adapter or create a new one
        self.adapter = ai_adapter or AIAdapter(
            api_key=api_key,
            model=model or CONFIG.get(f"{self.provider.upper()}_MODEL"),
            system_prompt=CONFIG.get(
                f"{self.provider.upper()}_SYSTEM_PROMPT", "You are a helpful assistant."
            ),
            provider=self.provider,
        )

    def ask(self, prompt: str) -> str:
        """
        Ask a prompt to the AI model and return the response text.
        Simplified interface for quick queries.

        Args:
            prompt: The user prompt to send to the model.

        Returns:
            The AI-generated response string.
        """
        success, response = self.adapter.generate_completion(prompt=prompt)
        if not success:
            logger.error(f"AI query failed: {response}")
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
        Process a text query and return an AI response with document context.

        Parameters:
            query_text (str): The user's query.
            context (dict, optional): Additional context as a dictionary.
            structured_content (list[dict] or dict, optional): Structured document content.
            context_window (int, optional): Number of most recent pages to include.
            selected_pages (list[int] or list[str], optional): Specific pages to include.

        Returns:
            str: AI-generated response.
        """
        success, response = self.adapter.generate_structured_completion(
            query_text=query_text,
            context=context,
            structured_content=structured_content,
            context_window=context_window,
            selected_pages=selected_pages,
        )

        if not success:
            logger.error(f"AI structured query failed: {response}")
            return ""
        return response
