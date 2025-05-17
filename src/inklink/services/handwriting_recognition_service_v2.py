"""Enhanced handwriting recognition service with multiple backend support."""

import logging
import os
import re
import tempfile
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests

from inklink.adapters.claude_vision_adapter import ClaudeVisionAdapter
from inklink.adapters.ollama_vision_adapter import OllamaVisionAdapter
from inklink.config import CONFIG
from inklink.services.interfaces import IHandwritingRecognitionService
from inklink.utils import format_error

logger = logging.getLogger(__name__)


class RecognitionBackend(Enum):
    """Available handwriting recognition backends."""

    CLAUDE_VISION = "claude_vision"
    OLLAMA_VISION = "ollama_vision"
    AUTO = "auto"  # Try Ollama first, fallback to Claude


class HandwritingRecognitionServiceV2(IHandwritingRecognitionService):
    """
    Enhanced handwriting recognition service with support for multiple backends.
    Supports both Claude Vision CLI and Ollama vision models.
    """

    def __init__(
        self,
        backend: RecognitionBackend = RecognitionBackend.AUTO,
        claude_command: Optional[str] = None,
        claude_model: Optional[str] = None,
        ollama_model: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        handwriting_adapter: Optional[ClaudeVisionAdapter] = None,
    ):
        """
        Initialize the handwriting recognition service.

        Args:
            backend: Which backend to use (claude_vision, ollama_vision, or auto)
            claude_command: Optional command to invoke Claude CLI
            claude_model: Optional model specification for Claude CLI
            ollama_model: Optional Ollama vision model name
            ollama_base_url: Optional Ollama API base URL
            handwriting_adapter: Optional pre-configured Claude adapter
        """
        self.backend = backend

        # Claude Vision setup
        self.claude_command = (
            claude_command
            or os.environ.get("CLAUDE_COMMAND")
            or CONFIG.get("CLAUDE_COMMAND", "/home/ryan/.claude/local/claude")
        )
        self.claude_model = (
            claude_model
            or os.environ.get("CLAUDE_MODEL")
            or CONFIG.get("CLAUDE_MODEL", "")
        )

        # Ollama Vision setup
        self.ollama_model = (
            ollama_model
            or os.environ.get("OLLAMA_VISION_MODEL")
            or CONFIG.get("OLLAMA_VISION_MODEL", "qwen2.5vl:32b-q4_K_M")
        )
        self.ollama_base_url = (
            ollama_base_url
            or os.environ.get("OLLAMA_BASE_URL")
            or CONFIG.get("OLLAMA_BASE_URL", "http://localhost:11434")
        )

        # Initialize adapters
        self.claude_adapter = handwriting_adapter or ClaudeVisionAdapter(
            claude_command=self.claude_command, model=self.claude_model
        )
        self.ollama_adapter = OllamaVisionAdapter(base_url=self.ollama_base_url)

        # Cache for recent recognitions
        self._recognition_cache: Dict[str, str] = {}

        logger.info(f"Initialized with backend: {self.backend.value}")
        if self.backend in [RecognitionBackend.OLLAMA_VISION, RecognitionBackend.AUTO]:
            logger.info(f"Ollama model: {self.ollama_model}")

    async def recognize_handwriting(
        self, image_data: Any, format: str = "text"
    ) -> Optional[str]:
        """
        Recognize handwriting in the given image data.

        Args:
            image_data: Either a file path (str), bytes, or PIL Image
            format: Output format ('text' or 'json')

        Returns:
            Recognized text or None if recognition fails
        """
        if self.backend == RecognitionBackend.CLAUDE_VISION:
            return await self._recognize_with_claude(image_data, format)
        elif self.backend == RecognitionBackend.OLLAMA_VISION:
            return await self._recognize_with_ollama(image_data, format)
        else:  # AUTO
            # Try Ollama first, fallback to Claude
            result = await self._recognize_with_ollama(image_data, format)
            if not result or result.strip() == "":
                logger.info("Ollama recognition failed, falling back to Claude")
                result = await self._recognize_with_claude(image_data, format)
            return result

    async def _recognize_with_claude(
        self, image_data: Any, format: str = "text"
    ) -> Optional[str]:
        """Recognize handwriting using Claude Vision."""
        try:
            # Handle different image data types
            image_path = None
            temp_file = None

            if isinstance(image_data, str):
                # File path
                image_path = image_data
            elif isinstance(image_data, bytes):
                # Raw bytes
                temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                temp_file.write(image_data)
                temp_file.close()
                image_path = temp_file.name
            else:
                # Assume PIL Image
                temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                image_data.save(temp_file.name)
                temp_file.close()
                image_path = temp_file.name

            # Use Claude Vision adapter
            prompt = "Please transcribe all handwritten text in this image accurately."
            result = await self.claude_adapter.analyze_image(image_path, prompt)

            # Clean up temp file if used
            if temp_file:
                os.unlink(temp_file.name)

            return result

        except Exception as e:
            logger.error(f"Error in Claude handwriting recognition: {e}")
            return None

    async def _recognize_with_ollama(
        self, image_data: Any, format: str = "text"
    ) -> Optional[str]:
        """Recognize handwriting using Ollama Vision."""
        try:
            # Handle different image data types
            image_path = None
            temp_file = None

            if isinstance(image_data, str):
                # File path
                image_path = image_data
            elif isinstance(image_data, bytes):
                # Raw bytes
                temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                temp_file.write(image_data)
                temp_file.close()
                image_path = temp_file.name
            else:
                # Assume PIL Image
                temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                image_data.save(temp_file.name)
                temp_file.close()
                image_path = temp_file.name

            # Use Ollama Vision adapter
            result = await self.ollama_adapter.query_handwriting(
                image_path=image_path, model=self.ollama_model
            )

            # Clean up temp file if used
            if temp_file:
                os.unlink(temp_file.name)

            # Handle JSON format if requested
            if format == "json" and result:
                # For now, return a simple JSON structure
                return f'{{"text": "{result}"}}'

            return result

        except Exception as e:
            logger.error(f"Error in Ollama handwriting recognition: {e}")
            return None

    def recognize_batch(
        self, images: List[Any], format: str = "text"
    ) -> List[Optional[str]]:
        """
        Recognize handwriting in multiple images.

        Args:
            images: List of image data
            format: Output format ('text' or 'json')

        Returns:
            List of recognized text
        """
        import asyncio

        async def _batch_recognize():
            tasks = [self.recognize_handwriting(img, format) for img in images]
            return await asyncio.gather(*tasks)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_batch_recognize())
        finally:
            loop.close()

    def recognize_from_url(self, url: str, format: str = "text") -> Optional[str]:
        """
        Recognize handwriting from an image URL.

        Args:
            url: URL of the image
            format: Output format ('text' or 'json')

        Returns:
            Recognized text or None if recognition fails
        """
        try:
            # Download the image
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.recognize_handwriting(response.content, format)
                )
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Error recognizing from URL {url}: {e}")
            return None

    def preprocess_image(self, image_data: Any) -> Any:
        """
        Preprocess image for better recognition accuracy.

        Args:
            image_data: Input image data

        Returns:
            Preprocessed image data
        """
        # For now, just pass through
        # In the future, could add image enhancement, denoising, etc.
        return image_data

    def extract_lines(self, text: str) -> List[str]:
        """
        Extract individual lines from recognized text.

        Args:
            text: Recognized text

        Returns:
            List of lines
        """
        if not text:
            return []

        # Split by newlines and filter empty lines
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return lines

    def extract_words(self, text: str) -> List[str]:
        """
        Extract individual words from recognized text.

        Args:
            text: Recognized text

        Returns:
            List of words
        """
        if not text:
            return []

        # Split by whitespace and punctuation
        words = re.findall(r"\b\w+\b", text)
        return words

    def detect_language(self, text: str) -> str:
        """
        Detect the language of recognized text.

        Args:
            text: Recognized text

        Returns:
            Language code
        """
        # For now, assume English
        # In the future, could use language detection library
        return "en"

    async def get_backend_info(self) -> Dict[str, Any]:
        """Get information about the active backend."""
        info = {"backend": self.backend.value, "available_backends": []}

        # Check Claude availability
        try:
            # Simple test to see if Claude is available
            await self.claude_adapter.analyze_image("/dev/null", "test", test_mode=True)
            info["available_backends"].append("claude_vision")
        except Exception as e:
            logger.debug(f"Claude Vision not available: {e}")

        # Check Ollama availability
        try:
            models = await self.ollama_adapter.list_models()
            vision_models = [
                m
                for m in models
                if any(
                    x in m.get("name", "").lower()
                    for x in ["vision", "vl", "multimodal", "mm"]
                )
            ]
            if vision_models:
                info["available_backends"].append("ollama_vision")
                info["ollama_vision_models"] = [m.get("name") for m in vision_models]
        except Exception as e:
            logger.debug(f"Ollama Vision not available: {e}")

        return info
