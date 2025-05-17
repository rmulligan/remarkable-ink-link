#!/usr/bin/env python
"""
Code Recognition Service for detecting and processing handwritten pseudocode.

This service enhances the handwriting recognition pipeline to:
1. Detect #code tags that trigger code generation
2. Identify pseudocode patterns in handwritten notes
3. Extract and format code blocks
4. Route to appropriate code generation services
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from inklink.services.interfaces import IHandwritingRecognitionService

logger = logging.getLogger(__name__)


class CodeRecognitionService:
    """Service for detecting and processing handwritten code/pseudocode."""

    def __init__(
        self,
        handwriting_service: IHandwritingRecognitionService,
        enable_auto_detection: bool = True,
        code_tag: str = "code",
        pseudocode_tag: str = "pseudocode",
        algorithm_tag: str = "algorithm",
    ):
        """
        Initialize the code recognition service.

        Args:
            handwriting_service: Base handwriting recognition service
            enable_auto_detection: Whether to auto-detect pseudocode patterns
            code_tag: Tag that triggers code generation (#code)
            pseudocode_tag: Tag for explicit pseudocode (#pseudocode)
            algorithm_tag: Tag for algorithm descriptions (#algorithm)
        """
        self.handwriting_service = handwriting_service
        self.enable_auto_detection = enable_auto_detection
        self.code_tag = code_tag
        self.pseudocode_tag = pseudocode_tag
        self.algorithm_tag = algorithm_tag

        # Code detection patterns
        self.code_patterns = {
            "function": re.compile(
                r"\b(function|def|func|method|def\s+\w+|function\s+\w+)\s*\(",
                re.IGNORECASE,
            ),
            "class": re.compile(r"\b(class|struct|interface)\s+\w+", re.IGNORECASE),
            "control_flow": re.compile(
                r"\b(if\s+|while\s+|for\s+|else|elif|return|break|continue)\b",
                re.IGNORECASE,
            ),
            "variable": re.compile(
                r"\b(let|var|const|int|string|bool|float|double)\s+\w+", re.IGNORECASE
            ),
            "algorithm": re.compile(
                r"\b(algorithm|procedure|process|step\s+\d+|input|output)\b",
                re.IGNORECASE,
            ),
            "operators": re.compile(r"[<>]=?|==|!=|\+=|-=|\*=|/=|&&|\|\|"),
            "assignment": re.compile(r"\w+\s*[:=]\s*.+"),
            "braces": re.compile(r"[{}\[\]()]"),
            "comments": re.compile(r"//|/\*|\*/|#\s+.*"),
            "indentation": re.compile(r"^\s{2,}"),  # 2+ spaces at line start
        }

        # Language hint patterns
        self.language_patterns = {
            "python": re.compile(
                r"\b(def|import|from|print|len|range|self|__init__|:$)\b"
            ),
            "javascript": re.compile(
                r"\b(function|const|let|var|console\.log|=>|async|await)\b"
            ),
            "java": re.compile(
                r"\b(public|private|static|void|new|System\.out|class)\b"
            ),
            "cpp": re.compile(r"\b(std::|cout|cin|#include|namespace|template)\b"),
            "go": re.compile(r"\b(func|package|import|fmt\.|defer|go\s+)\b"),
            "rust": re.compile(r"\b(fn|mut|impl|match|Result|Option|pub)\b"),
        }

    def detect_code_content(self, text: str) -> Dict[str, Any]:
        """
        Detect if text contains code or pseudocode content.

        Args:
            text: The recognized handwritten text

        Returns:
            Dict with detection results:
            - is_code: Whether code content was detected
            - confidence: Confidence level (0-1)
            - tags: Detected tags (#code, #pseudocode, etc.)
            - patterns: Which patterns were detected
            - language_hints: Detected programming language hints
            - blocks: Extracted code blocks
        """
        result = {
            "is_code": False,
            "confidence": 0.0,
            "tags": [],
            "patterns": [],
            "language_hints": [],
            "blocks": [],
        }

        if not text:
            return result

        # 1. Check for explicit tags
        tag_pattern = re.compile(r"#(\w+)")
        tags = tag_pattern.findall(text.lower())

        code_tags = [self.code_tag, self.pseudocode_tag, self.algorithm_tag]
        detected_code_tags = [tag for tag in tags if tag in code_tags]

        if detected_code_tags:
            result["tags"] = detected_code_tags
            result["is_code"] = True
            result["confidence"] = 1.0

        # 2. Auto-detect code patterns if enabled
        if self.enable_auto_detection and not result["is_code"]:
            pattern_scores = {}
            total_score = 0

            for pattern_name, pattern in self.code_patterns.items():
                matches = pattern.findall(text)
                if matches:
                    pattern_scores[pattern_name] = len(matches)
                    total_score += len(matches)
                    result["patterns"].append(pattern_name)

            # Calculate confidence based on pattern matches
            if total_score > 0:
                # Normalize score (more matches = higher confidence)
                result["confidence"] = min(1.0, total_score / 10.0)
                result["is_code"] = result["confidence"] >= 0.5

        # 3. Detect language hints
        for lang, pattern in self.language_patterns.items():
            if pattern.search(text):
                result["language_hints"].append(lang)

        # 4. Extract code blocks
        if result["is_code"]:
            result["blocks"] = self._extract_code_blocks(text)

        return result

    def _extract_code_blocks(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract distinct code blocks from text.

        Args:
            text: The text containing code

        Returns:
            List of code blocks with metadata
        """
        blocks = []

        # Split text into sections by empty lines or tags
        sections = re.split(r"\n\s*\n", text)

        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue

            # Check if this section has code characteristics
            code_score = 0
            for pattern in self.code_patterns.values():
                if pattern.search(section):
                    code_score += 1

            if code_score >= 2:  # At least 2 patterns match
                block = {
                    "content": section,
                    "index": i,
                    "line_count": len(section.splitlines()),
                    "has_indentation": bool(
                        self.code_patterns["indentation"].search(section)
                    ),
                }

                # Try to detect the type of code block
                if self.code_patterns["function"].search(section):
                    block["type"] = "function"
                elif self.code_patterns["class"].search(section):
                    block["type"] = "class"
                elif self.code_patterns["algorithm"].search(section):
                    block["type"] = "algorithm"
                else:
                    block["type"] = "snippet"

                blocks.append(block)

        return blocks

    def recognize_with_code_detection(
        self,
        image_path: str,
        content_type: str = "Text",
        language: str = "en_US",
    ) -> Dict[str, Any]:
        """
        Recognize handwriting with enhanced code detection.

        Args:
            image_path: Path to the image file
            content_type: Initial content type guess
            language: Language code

        Returns:
            Recognition results with code detection metadata
        """
        # First, do standard handwriting recognition
        result = self.handwriting_service.recognize_handwriting(
            image_path, content_type, language
        )

        if not result.get("success", False):
            return result

        recognized_text = result.get("text", "")

        # Perform code detection on the recognized text
        code_detection = self.detect_code_content(recognized_text)

        # Enhance the result with code detection
        result["code_detection"] = code_detection

        # If code is detected, we might want to re-process with different settings
        if code_detection["is_code"]:
            logger.info(
                f"Code content detected with confidence {code_detection['confidence']}"
            )

            # If initial content type wasn't "Code", retry with better settings
            if content_type != "Code":
                logger.info("Re-processing with code-optimized settings")
                code_result = self.handwriting_service.recognize_handwriting(
                    image_path, "Code", language
                )

                if code_result.get("success", False):
                    # Merge the results
                    result["text"] = code_result.get("text", recognized_text)
                    result["optimized_for_code"] = True

        return result

    def process_code_page(self, page_path: str) -> Dict[str, Any]:
        """
        Process a page that potentially contains code/pseudocode.

        Args:
            page_path: Path to the .rm file

        Returns:
            Processing results with extracted code blocks
        """
        try:
            # Recognize handwriting with code detection
            result = self.recognize_with_code_detection(page_path)

            if not result.get("success", False):
                return result

            code_detection = result.get("code_detection", {})

            if code_detection.get("is_code", False):
                # Extract structured code information
                processed_blocks = []

                for block in code_detection.get("blocks", []):
                    processed_block = {
                        "content": block["content"],
                        "type": block["type"],
                        "language": (
                            code_detection.get("language_hints", ["generic"])[0]
                            if code_detection.get("language_hints")
                            else "generic"
                        ),
                        "needs_generation": "#" + self.code_tag
                        in block["content"].lower(),
                    }

                    # Clean up the content for code generation
                    processed_block["cleaned_content"] = self._clean_pseudocode(
                        block["content"]
                    )

                    processed_blocks.append(processed_block)

                result["code_blocks"] = processed_blocks
                result["requires_code_generation"] = any(
                    block["needs_generation"] for block in processed_blocks
                )

            return result

        except Exception as e:
            logger.error(f"Error processing code page: {e}")
            return {"success": False, "error": str(e)}

    def _clean_pseudocode(self, text: str) -> str:
        """
        Clean up handwritten pseudocode for better code generation.

        Args:
            text: Raw pseudocode text

        Returns:
            Cleaned pseudocode
        """
        # Remove tags
        text = re.sub(r"#\w+", "", text)

        # Standardize indentation
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            # Convert tabs to spaces
            line = line.replace("\t", "    ")

            # Detect indentation level
            indent_match = re.match(r"^(\s*)", line)
            if indent_match:
                indent_level = len(indent_match.group(1)) // 2
                cleaned_line = "    " * indent_level + line.strip()
            else:
                cleaned_line = line.strip()

            if cleaned_line:
                cleaned_lines.append(cleaned_line)

        return "\n".join(cleaned_lines)
