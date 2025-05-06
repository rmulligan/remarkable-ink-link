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

    def process_query(self, query_text, context=None):
        """Process a text query and return an AI response using OpenAI Chat API.
        Optionally include structured document context to improve relevance."""
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # Structure context as a system prompt if provided
        messages = []
        if context:
            messages.append({
                "role": "system",
                "content": f"Document context: {context}"
            })
        messages.append({"role": "user", "content": query_text})
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        # OpenAI returns choices[0].message.content
        return result["choices"][0]["message"]["content"].strip()