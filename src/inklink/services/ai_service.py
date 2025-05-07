import os
import requests


class AIService:
    """Service for AI text processing using OpenAI."""

    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_API_KEY")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        self.api_base = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
        if not self.api_key:
            raise ValueError("OpenAI API key must be set via OPENAI_API_KEY or AI_API_KEY environment variable.")

    def process_query(
        self,
        query_text,
        context=None,
        structured_content=None,
        context_window=None,
        selected_pages=None,
    ):
        """
        Process a text query and return an AI response using OpenAI Chat API.

        Parameters:
            query_text (str): The user's query.
            context (str, optional): Flat context string for backward compatibility.
            structured_content (list[dict] or dict, optional): Structured document content, e.g., list of pages with links.
            context_window (int, optional): Number of most recent pages to include as context.
            selected_pages (list[int] or list[str], optional): Specific pages to include as context.

        Returns:
            str: AI-generated response.
        """
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
                filtered_pages = [
                    p
                    for p in pages
                    if (
                        p.get("id") in selected_pages
                        or p.get("number") in selected_pages
                    )
                ]
            elif context_window:
                filtered_pages = pages[-context_window:]
            else:
                filtered_pages = pages

            for page in filtered_pages:
                title = page.get("title", f"Page {page.get('number', '')}")
                content = page.get("content", "")
                links = page.get("links", [])
                link_str = "Links: " + ", ".join(
                    [
                        f"{link_data.get('label', link_data.get('target', ''))} (to page {link_data.get('target', '')})"
                        for link_data in links
                    ]
                )
                context_snippets.append(f"{title}:\n{content}\n{link_str}".strip())

            system_prompt = "Relevant document context:\n" + "\n\n".join(
                context_snippets
            )
            messages.append({"role": "system", "content": system_prompt})
        elif context:
            # Fallback to flat context string
            messages.append(
                {"role": "system", "content": f"Document context: {context}"}
            )

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
