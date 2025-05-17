#!/usr/bin/env python
"""
Enhanced Handwriting Recognition Service with Code Detection.

This service extends the base handwriting recognition to include:
1. Automatic code/pseudocode detection
2. Tag-based workflow routing (#code, #review, #debug)
3. Integration with Claude Code for code generation
4. Improved formatting for code blocks
"""

import logging
from typing import Any, Dict, List, Optional

from inklink.adapters.claude_vision_adapter import ClaudeVisionAdapter
from inklink.services.code_recognition_service import CodeRecognitionService
from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)
from inklink.services.interfaces import IHandwritingRecognitionService
from inklink.services.llm_service_manager import LLMServiceManager

logger = logging.getLogger(__name__)


class EnhancedHandwritingService(HandwritingRecognitionService):
    """
    Enhanced handwriting recognition service with code detection capabilities.
    """

    def __init__(
        self,
        claude_command: Optional[str] = None,
        model: Optional[str] = None,
        handwriting_adapter: Optional[ClaudeVisionAdapter] = None,
        llm_manager: Optional[LLMServiceManager] = None,
        enable_code_detection: bool = True,
        enable_auto_routing: bool = True,
    ):
        """
        Initialize the enhanced handwriting service.

        Args:
            claude_command: Command to invoke Claude CLI
            model: Claude model specification
            handwriting_adapter: Pre-configured adapter
            llm_manager: LLM service manager for routing
            enable_code_detection: Whether to enable code detection
            enable_auto_routing: Whether to automatically route to appropriate services
        """
        super().__init__(claude_command, model, handwriting_adapter)

        self.enable_code_detection = enable_code_detection
        self.enable_auto_routing = enable_auto_routing

        # Initialize code recognition service
        self.code_recognition = CodeRecognitionService(
            handwriting_service=self, enable_auto_detection=True
        )

        # Initialize LLM manager if not provided
        self.llm_manager = llm_manager or LLMServiceManager()

        # Tag-to-action mapping
        self.tag_actions = {
            "code": "generate_code",
            "review": "review_code",
            "debug": "debug_code",
            "explain": "explain_code",
            "optimize": "optimize_code",
            "test": "generate_tests",
        }

    def recognize_handwriting(
        self,
        image_path: str,
        content_type: str = "Text",
        language: str = "en_US",
    ) -> Dict[str, Any]:
        """
        Enhanced handwriting recognition with code detection.

        Args:
            image_path: Path to the image file
            content_type: Content type (Text, Diagram, Math, Code)
            language: Language code

        Returns:
            Recognition results with enhanced metadata
        """
        # Use the enhanced code recognition if enabled
        if self.enable_code_detection:
            result = self.code_recognition.recognize_with_code_detection(
                image_path, content_type, language
            )
        else:
            # Fall back to standard recognition
            result = super().recognize_handwriting(image_path, content_type, language)

        # Process the result for routing if enabled
        if self.enable_auto_routing and result.get("success", False):
            result = self._process_for_routing(result)

        return result

    def _process_for_routing(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process recognition results for automatic routing.

        Args:
            result: Recognition result dictionary

        Returns:
            Enhanced result with routing information
        """
        code_detection = result.get("code_detection", {})

        # Extract tags and determine actions
        tags = code_detection.get("tags", [])
        actions = []

        for tag in tags:
            if tag in self.tag_actions:
                actions.append(self.tag_actions[tag])

        # Add routing information
        result["routing"] = {
            "detected_tags": tags,
            "suggested_actions": actions,
            "is_code_content": code_detection.get("is_code", False),
            "confidence": code_detection.get("confidence", 0.0),
        }

        # If code is detected but no specific action tag, default to generate_code
        if code_detection.get("is_code", False) and not actions:
            result["routing"]["suggested_actions"] = ["generate_code"]

        return result

    def process_ink_with_routing(
        self,
        ink_data: Optional[bytes] = None,
        file_path: Optional[str] = None,
        content_type: Optional[str] = None,
        language: str = "en_US",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process ink data with automatic routing to appropriate services.

        Args:
            ink_data: Binary ink data
            file_path: Path to .rm file
            content_type: Content type
            language: Language code
            session_id: Optional session ID for context

        Returns:
            Processing results with service responses
        """
        # First, recognize the handwriting
        result = self.recognize_from_ink(ink_data, file_path, content_type, language)

        if not result.get("success", False):
            return result

        # Check routing information
        routing = result.get("routing", {})
        if not routing.get("suggested_actions"):
            return result

        # Process each suggested action
        service_results = {}
        text = result.get("text", "")
        code_blocks = result.get("code_blocks", [])

        for action in routing["suggested_actions"]:
            if action == "generate_code":
                service_results[action] = self._generate_code(
                    text, code_blocks, session_id
                )
            elif action == "review_code":
                service_results[action] = self._review_code(
                    text, code_blocks, session_id
                )
            elif action == "debug_code":
                service_results[action] = self._debug_code(
                    text, code_blocks, session_id
                )
            # Add more actions as needed

        result["service_results"] = service_results
        return result

    def _generate_code(
        self,
        text: str,
        code_blocks: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate code using the LLM manager.

        Args:
            text: Full recognized text
            code_blocks: Extracted code blocks
            session_id: Optional session ID

        Returns:
            Code generation results
        """
        try:
            # Use the first code block or the full text
            prompt = code_blocks[0]["cleaned_content"] if code_blocks else text

            # Determine the language hint
            language = None
            if code_blocks and code_blocks[0].get("language") != "generic":
                language = code_blocks[0].get("language")

            # Route through LLM manager
            result = self.llm_manager.route_task(
                task_type="code_generation",
                content=prompt,
                language=language,
                session_id=session_id,
            )

            return result

        except Exception as e:
            logger.error(f"Error generating code: {e}")
            return {"success": False, "error": str(e)}

    def _review_code(
        self,
        text: str,
        code_blocks: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Review code using the LLM manager.

        Args:
            text: Full recognized text
            code_blocks: Extracted code blocks
            session_id: Optional session ID

        Returns:
            Code review results
        """
        try:
            # Extract the code to review
            code_to_review = code_blocks[0]["content"] if code_blocks else text

            # Route through LLM manager
            result = self.llm_manager.route_task(
                task_type="code_review",
                content=code_to_review,
                session_id=session_id,
            )

            return result

        except Exception as e:
            logger.error(f"Error reviewing code: {e}")
            return {"success": False, "error": str(e)}

    def _debug_code(
        self,
        text: str,
        code_blocks: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Debug code using the LLM manager.

        Args:
            text: Full recognized text
            code_blocks: Extracted code blocks
            session_id: Optional session ID

        Returns:
            Debug results
        """
        try:
            # Extract code and error information
            if code_blocks:
                code = code_blocks[0]["content"]
                # Look for error description in the text
                error_msg = self._extract_error_message(text)
            else:
                code = text
                error_msg = "Please identify and fix any issues in this code"

            # Route through LLM manager
            result = self.llm_manager.route_task(
                task_type="debugging",
                content=code,
                error_message=error_msg,
                session_id=session_id,
            )

            return result

        except Exception as e:
            logger.error(f"Error debugging code: {e}")
            return {"success": False, "error": str(e)}

    def _extract_error_message(self, text: str) -> str:
        """
        Extract error message from text.

        Args:
            text: Full text that might contain error description

        Returns:
            Extracted error message or default message
        """
        # Look for common error patterns
        import re

        error_patterns = [
            r"error[:\s]+(.+?)(?:\n|$)",
            r"exception[:\s]+(.+?)(?:\n|$)",
            r"bug[:\s]+(.+?)(?:\n|$)",
            r"issue[:\s]+(.+?)(?:\n|$)",
            r"problem[:\s]+(.+?)(?:\n|$)",
        ]

        for pattern in error_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "Please identify and fix any issues in this code"
