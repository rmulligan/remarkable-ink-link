"""AI Service for interacting with OpenAI models."""

import os
import requests
from typing import Optional, Dict, Any, List, Union

from inklink.utils import retry_operation, format_error
from inklink.config import CONFIG

logger = logging.getLogger(__name__)



class AIService:
    """Service for AI text processing using OpenAI."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize AIService with model and API key.

        Args:
            api_key: OpenAI API key; falls back to OPENAI_API_KEY env var.
            model: OpenAI model name (e.g., 'gpt-3.5-turbo').
        """
        self.api_key = (
            api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_API_KEY")
        )
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set; AIService may not work.")
        self.model = model or CONFIG.get("OPENAI_MODEL", "gpt-3.5-turbo")
        self.system_prompt = CONFIG.get(
            "OPENAI_SYSTEM_PROMPT", "You are a helpful assistant."
        )
        self.api_base = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")

    def ask(self, prompt: str) -> str:
        """
        Ask a prompt to the AI model and return the response text.
        Simplified interface for quick queries.

        Args:
            prompt: The user prompt to send to the model.

        Returns:
            The AI-generated response string.
        """
        return self.process_query(prompt)

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
        Process a text query and return an AI response using OpenAI Chat API.

        Parameters:
            query_text (str): The user's query.
            context (dict, optional): Additional context as a dictionary.
            structured_content (list[dict] or dict, optional): Structured document content, e.g., list of pages with links.
            context_window (int, optional): Number of most recent pages to include as context.
            selected_pages (list[int] or list[str], optional): Specific pages to include as context.

        Returns:
            str: AI-generated response.
        """
        def call_api():
            url = f"{self.api_base}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            messages = []

            # Build system prompt from structured_content if provided
            if structured_content:
                context_snippets = []
                pages = []
                # Determine which pages to include
                if isinstance(structured_content, dict):
                    pages = structured_content.get("pages", [])
                elif isinstance(structured_content, list):
                    pages = structured_content
                else:
                    pages = []

                # Select pages based on context_window or selected_pages
                if selected_pages:
                    filtered = [
                        p
                        for p in pages
                        if (
                            p.get("id") in selected_pages
                            or p.get("number") in selected_pages
                        )
                    ]
                elif context_window:
                    filtered = pages[-context_window:]
                else:
                    filtered = pages

                for page in filtered:
                    title = page.get("title", f"Page {page.get('number', '')}")
                    content = page.get("content", "")
                    links = page.get("links", [])
                    link_str = ""
                    if links:
                        link_str = "Links: " + ", ".join(
                            [
                                f"{l.get('label', l.get('target', ''))} (to page {l.get('target', '')})"
                                for l in links
                            ]
                        )
                    context_snippets.append(f"{title}:\n{content}\n{link_str}".strip())

                system_prompt = "Relevant document context:\n" + "\n\n".join(
                    context_snippets
                )
                messages.append({"role": "system", "content": system_prompt})
            elif context:
                # Fallback to context object
                context_str = ", ".join([f"{k}: {v}" for k, v in context.items() if v])
                messages.append(
                    {"role": "system", "content": f"Document context: {context_str}"}
                )
            else:
                # Use default system prompt if no context provided
                messages.append({"role": "system", "content": self.system_prompt})

            messages.append({"role": "user", "content": query_text})

            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7,
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            # OpenAI returns choices[0].message.content
            return result["choices"][0]["message"]["content"].strip()

        try:
            return retry_operation(call_api, operation_name="AIService.process_query")
        except Exception as e:
            logger.error(format_error("ai", "Failed to get AI response", e))
            return ""
