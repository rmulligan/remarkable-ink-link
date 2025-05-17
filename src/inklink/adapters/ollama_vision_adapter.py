"""Ollama adapter with vision support for local multimodal LLMs."""

import base64
import json
import logging
from typing import Any, Dict, List, Optional, Union

import aiohttp


class OllamaVisionAdapter:
    """Adapter for interacting with Ollama multimodal vision-language models."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize the Ollama vision adapter."""
        self.base_url = base_url
        self.logger = logging.getLogger("inklink.ollama_vision")
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

    async def query_vision(
        self,
        model: str,
        prompt: str,
        images: Union[str, List[str]],
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Query a vision model with text and images.

        Args:
            model: Model name (e.g., 'qwen2.5vl:32b-q4_K_M')
            prompt: Text prompt
            images: Image path(s) or base64 encoded image(s)
            context: Optional context
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate

        Returns:
            Model response text
        """
        await self._ensure_session()

        try:
            # Convert images to list if single image
            if isinstance(images, str):
                images = [images]

            # Process images - convert to base64 if file paths
            processed_images = []
            for image in images:
                if image.startswith("data:image") or image.startswith("/"):
                    # Already base64 or needs to be loaded
                    if image.startswith("/"):
                        # Load from file
                        image = await self._encode_image_file(image)
                    processed_images.append(image)
                else:
                    # Assume it's already base64
                    processed_images.append(image)

            # Prepare messages
            messages = []

            if context:
                messages.append({"role": "system", "content": f"Context: {context}"})

            # Add user message with images
            user_message = {
                "role": "user",
                "content": prompt,
                "images": processed_images,
            }
            messages.append(user_message)

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
                error_text = await response.text()
                self.logger.error(f"Error response: {error_text}")
                return ""

        except Exception as e:
            self.logger.error(f"Error querying vision model: {e}")
            return ""

    async def _encode_image_file(self, file_path: str) -> str:
        """Encode an image file to base64."""
        try:
            with open(file_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode("utf-8")
                # Detect image type from file extension
                if file_path.lower().endswith(".png"):
                    mime_type = "image/png"
                elif file_path.lower().endswith(".jpg") or file_path.lower().endswith(
                    ".jpeg"
                ):
                    mime_type = "image/jpeg"
                else:
                    mime_type = "image/png"  # Default
                return f"data:{mime_type};base64,{encoded}"
        except Exception as e:
            self.logger.error(f"Error encoding image file {file_path}: {e}")
            raise

    async def query_handwriting(
        self,
        image_path: str,
        model: str = "qwen2.5vl:32b-q4_K_M",
        temperature: float = 0.3,  # Lower temperature for OCR accuracy
        system_prompt: str = None,
    ) -> str:
        """Specialized method for handwriting recognition.

        Args:
            image_path: Path to handwriting image
            model: Vision model to use
            temperature: Temperature (lower is better for OCR)
            system_prompt: Optional system prompt

        Returns:
            Recognized text
        """
        if not system_prompt:
            system_prompt = """You are a handwriting recognition expert. Your task is to accurately transcribe handwritten text from images.
Focus on:
1. Accurate character recognition
2. Preserving the original formatting and line breaks
3. Identifying mathematical symbols and equations if present
4. Noting any unclear or ambiguous text with [?]
5. Maintaining the original spelling and grammar, even if incorrect

Please provide the transcribed text exactly as it appears in the image."""

        prompt = "Please transcribe all the handwritten text in this image accurately. Preserve line breaks and formatting."

        return await self.query_vision(
            model=model,
            prompt=prompt,
            images=image_path,
            context=system_prompt,
            temperature=temperature,
            max_tokens=2000,  # Longer for potentially lengthy handwritten content
        )

    async def stream_query_vision(
        self,
        model: str,
        prompt: str,
        images: Union[str, List[str]],
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        """Stream query results from a vision model."""
        await self._ensure_session()

        try:
            # Process images similar to query_vision
            if isinstance(images, str):
                images = [images]

            processed_images = []
            for image in images:
                if image.startswith("/"):
                    image = await self._encode_image_file(image)
                processed_images.append(image)

            messages = []

            if context:
                messages.append({"role": "system", "content": f"Context: {context}"})

            user_message = {
                "role": "user",
                "content": prompt,
                "images": processed_images,
            }
            messages.append(user_message)

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
                            message = chunk.get("message", {})
                            if message.get("content"):
                                yield message.get("content")
                else:
                    self.logger.error(f"Stream query failed: {response.status}")

        except Exception as e:
            self.logger.error(f"Error in stream query: {e}")
