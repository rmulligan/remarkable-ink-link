"""Enhanced Ollama adapter with better error handling and configuration."""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientTimeout

from inklink.agents.exceptions import (
    OllamaConnectionError,
    OllamaModelError,
    OllamaQueryError,
)


@dataclass
class OllamaConfig:
    """Configuration for Ollama adapter."""

    base_url: str = "http://localhost:11434"
    timeout: int = 600  # seconds
    retry_attempts: int = 3
    retry_delay: float = 1.0  # seconds
    max_concurrent_requests: int = 5


class OllamaAdapter:
    """Enhanced Ollama adapter with better error handling."""

    def __init__(self, config: Optional[OllamaConfig] = None):
        """Initialize the Ollama adapter."""
        self.config = config or OllamaConfig()
        self.logger = logging.getLogger("inklink.ollama")
        self.session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            self.session = None

    async def _ensure_session(self):
        """Ensure aiohttp session exists with proper configuration."""
        if not self.session:
            timeout = ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def _request_with_retry(
        self, method: str, url: str, **kwargs
    ) -> aiohttp.ClientResponse:
        """Make a request with retry logic."""
        last_error = None

        for attempt in range(self.config.retry_attempts):
            try:
                async with self._semaphore:  # Rate limiting
                    await self._ensure_session()

                    async with self.session.request(method, url, **kwargs) as response:
                        if response.status >= 500:  # Server errors, retry
                            if attempt < self.config.retry_attempts - 1:
                                await asyncio.sleep(
                                    self.config.retry_delay * (2**attempt)
                                )
                                continue
                            else:
                                raise OllamaConnectionError(
                                    f"Server error: {response.status} - {await response.text()}"
                                )

                        return response

            except aiohttp.ClientError as e:
                last_error = e
                if attempt < self.config.retry_attempts - 1:
                    self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(self.config.retry_delay * (2**attempt))
                else:
                    raise OllamaConnectionError(
                        f"Failed after {self.config.retry_attempts} attempts: {e}"
                    )

            except asyncio.TimeoutError:
                raise OllamaConnectionError(
                    f"Request timed out after {self.config.timeout} seconds"
                )

        raise OllamaConnectionError(
            f"Failed after {self.config.retry_attempts} attempts: {last_error}"
        )

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        try:
            response = await self._request_with_retry(
                "GET", f"{self.config.base_url}/api/tags"
            )

            if response.status == 200:
                data = await response.json()
                return data.get("models", [])
            else:
                raise OllamaModelError(f"Failed to list models: {response.status}")

        except OllamaConnectionError:
            raise
        except Exception as e:
            self.logger.error(f"Error listing models: {e}")
            raise OllamaModelError(f"Unexpected error listing models: {e}")

    async def model_exists(self, model_name: str) -> bool:
        """Check if a model exists."""
        try:
            models = await self.list_models()
            return any(model["name"] == model_name for model in models)
        except Exception as e:
            self.logger.error(f"Error checking model existence: {e}")
            return False

    async def pull_model(self, model_name: str, progress_callback=None) -> bool:
        """Pull a model from Ollama registry with progress tracking."""
        try:
            data = {"name": model_name}

            async with self.session.post(
                f"{self.config.base_url}/api/pull", json=data
            ) as response:
                if response.status == 200:
                    async for line in response.content:
                        if line:
                            progress = json.loads(line)
                            self.logger.info(f"Pull progress: {progress}")

                            if progress_callback:
                                await progress_callback(progress)

                    return True
                else:
                    error_text = await response.text()
                    raise OllamaModelError(f"Failed to pull model: {error_text}")

        except OllamaConnectionError:
            raise
        except Exception as e:
            self.logger.error(f"Error pulling model: {e}")
            raise OllamaModelError(f"Unexpected error pulling model: {e}")

    async def query(
        self,
        model: str,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Query a model with enhanced error handling."""
        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            if context:
                messages.append({"role": "system", "content": f"Context: {context}"})

            messages.append({"role": "user", "content": prompt})

            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }

            response = await self._request_with_retry(
                "POST", f"{self.config.base_url}/api/chat", json=data
            )

            if response.status == 200:
                result = await response.json()
                return result["message"]["content"]
            else:
                error = await response.text()
                raise OllamaQueryError(f"Query failed: {error}")

        except (OllamaConnectionError, OllamaQueryError):
            raise
        except Exception as e:
            self.logger.error(f"Error querying model: {e}")
            raise OllamaQueryError(f"Unexpected error querying model: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for Ollama service."""
        try:
            start_time = asyncio.get_event_loop().time()

            # Check basic connectivity
            response = await self._request_with_retry("GET", f"{self.config.base_url}/")
            is_healthy = response.status == 200

            # Check model availability
            models = await self.list_models() if is_healthy else []

            elapsed_time = asyncio.get_event_loop().time() - start_time

            return {
                "healthy": is_healthy,
                "response_time": elapsed_time,
                "available_models": [model["name"] for model in models],
                "model_count": len(models),
                "base_url": self.config.base_url,
            }

        except Exception as e:
            return {"healthy": False, "error": str(e), "base_url": self.config.base_url}
