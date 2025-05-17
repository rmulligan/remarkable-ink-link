"""Ollama adapter for local LLM integration."""

import json
import logging
from typing import Any, Dict, List, Optional

import aiohttp


class OllamaAdapter:
    """Adapter for interacting with Ollama local LLMs."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize the Ollama adapter."""
        self.base_url = base_url
        self.logger = logging.getLogger("inklink.ollama")
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        await self._ensure_session()

        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("models", [])
                self.logger.error(f"Failed to list models: {response.status}")
                return []
        except Exception as e:
            self.logger.error(f"Error listing models: {e}")
            return []

    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        await self._ensure_session()

        try:
            data = {"name": model_name}
            async with self.session.post(
                f"{self.base_url}/api/pull", json=data
            ) as response:
                if response.status == 200:
                    # Stream the response to track progress
                    async for line in response.content:
                        if line:
                            # Decode bytes to string before JSON parsing
                            progress = json.loads(line.decode("utf-8"))
                            self.logger.info(f"Pull progress: {progress}")
                    return True
                self.logger.error(f"Failed to pull model: {response.status}")
                return False
        except Exception as e:
            self.logger.error(f"Error pulling model: {e}")
            return False

    async def query(
        self,
        model: str,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Query a model with a prompt."""
        await self._ensure_session()

        try:
            # Prepare the request
            messages = []

            if context:
                messages.append({"role": "system", "content": f"Context: {context}"})

            messages.append({"role": "user", "content": prompt})

            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "options": {"num_predict": max_tokens},
                "stream": False,
            }

            # Make the request
            async with self.session.post(
                f"{self.base_url}/api/chat", json=data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("message", {}).get("content", "")
                self.logger.error(f"Query failed: {response.status}")
                return ""

        except Exception as e:
            self.logger.error(f"Error querying model: {e}")
            return ""

    async def stream_query(
        self,
        model: str,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        """Stream query results."""
        await self._ensure_session()

        try:
            # Prepare the request similar to query
            messages = []

            if context:
                messages.append({"role": "system", "content": f"Context: {context}"})

            messages.append({"role": "user", "content": prompt})

            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "options": {"num_predict": max_tokens},
                "stream": True,
            }

            async with self.session.post(
                f"{self.base_url}/api/chat", json=data
            ) as response:
                if response.status == 200:
                    async for line in response.content:
                        if line:
                            # Decode bytes to string before JSON parsing
                            chunk = json.loads(line.decode("utf-8"))
                            if chunk.get("done", False):
                                return
                            yield chunk.get("message", {}).get("content", "")
                else:
                    self.logger.error(f"Stream query failed: {response.status}")

        except Exception as e:
            self.logger.error(f"Error streaming query: {e}")

    async def create_model(
        self, name: str, modelfile: str, path: Optional[str] = None
    ) -> bool:
        """Create a new model."""
        await self._ensure_session()

        try:
            data = {"name": name, "modelfile": modelfile}
            if path:
                data["path"] = path

            async with self.session.post(
                f"{self.base_url}/api/create", json=data
            ) as response:
                if response.status == 200:
                    # Stream the response
                    async for line in response.content:
                        if line:
                            # Decode bytes to string before JSON parsing
                            status = json.loads(line.decode("utf-8"))
                            self.logger.info(f"Create model status: {status}")
                    return True
                self.logger.error(f"Failed to create model: {response.status}")
                return False

        except Exception as e:
            self.logger.error(f"Error creating model: {e}")
            return False

    async def delete_model(self, name: str) -> bool:
        """Delete a model."""
        await self._ensure_session()

        try:
            data = {"name": name}
            async with self.session.delete(
                f"{self.base_url}/api/delete", json=data
            ) as response:
                return response.status == 200

        except Exception as e:
            self.logger.error(f"Error deleting model: {e}")
            return False

    async def model_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get model information."""
        await self._ensure_session()

        try:
            data = {"name": name}
            async with self.session.post(
                f"{self.base_url}/api/show", json=data
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None

        except Exception as e:
            self.logger.error(f"Error getting model info: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        await self._ensure_session()

        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                return response.status == 200
        except Exception:
            return False
