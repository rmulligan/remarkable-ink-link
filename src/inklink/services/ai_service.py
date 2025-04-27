"""AI Service for interacting with OpenAI models."""

import os
import logging
from typing import Optional

import openai

from inklink.utils import retry_operation, format_error
from inklink.config import CONFIG

logger = logging.getLogger(__name__)


class AIService:
    """Service to query AI models via OpenAI API."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize AIService with model and API key.

        Args:
            model: OpenAI model name (e.g., 'gpt-3.5-turbo').
            api_key: OpenAI API key; falls back to OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key
        else:
            logger.warning("OPENAI_API_KEY not set; AIService may not work.")
        self.model = model or CONFIG.get("OPENAI_MODEL")
        self.system_prompt = CONFIG.get("OPENAI_SYSTEM_PROMPT")

    def ask(self, prompt: str) -> str:
        """
        Ask a prompt to the AI model and return the response text.

        Args:
            prompt: The user prompt to send to the model.

        Returns:
            The AI-generated response string.
        """
        def call_api():
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            # Extract and return the assistant message
            choice = response.choices[0].message
            return choice.content.strip()

        try:
            return retry_operation(call_api, operation_name="AIService.ask")
        except Exception as e:
            logger.error(format_error("ai", "Failed to get AI response", e))
            return ""