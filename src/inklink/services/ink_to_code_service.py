#!/usr/bin/env python
"""
Ink-to-Code Service for converting handwritten pseudocode to executable code.

This service implements the complete workflow:
1. Handwriting recognition with Claude Vision
2. Pseudocode/code detection
3. Code generation with Claude Code
4. Response formatting in .rm format
5. Upload back to reMarkable
"""

import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from inklink.config import CONFIG
from inklink.services.document_service import DocumentService
from inklink.services.enhanced_handwriting_service import EnhancedHandwritingService
from inklink.services.llm_service_manager import LLMServiceManager
from inklink.services.remarkable_service import RemarkableService
from inklink.utils.retry import retry

logger = logging.getLogger(__name__)


class InkToCodeService:
    """Service for converting handwritten code/pseudocode to executable code."""

    def __init__(
        self,
        handwriting_service: Optional[EnhancedHandwritingService] = None,
        llm_manager: Optional[LLMServiceManager] = None,
        document_service: Optional[DocumentService] = None,
        remarkable_service: Optional[RemarkableService] = None,
        enable_syntax_highlighting: bool = True,
    ):
        """
        Initialize the Ink-to-Code service.

        Args:
            handwriting_service: Enhanced handwriting recognition service
            llm_manager: LLM service manager for code generation
            document_service: Service for document creation
            remarkable_service: Service for reMarkable upload
            enable_syntax_highlighting: Whether to enable syntax highlighting
        """
        self.temp_dir = CONFIG.get("TEMP_DIR")
        os.makedirs(self.temp_dir, exist_ok=True)

        # Initialize services
        self.handwriting_service = handwriting_service or EnhancedHandwritingService()
        self.llm_manager = llm_manager or LLMServiceManager()
        self.document_service = document_service or DocumentService(
            self.temp_dir, CONFIG.get("DRAWJ2D_PATH")
        )
        self.remarkable_service = remarkable_service or RemarkableService(
            CONFIG.get("RMAPI_PATH"), CONFIG.get("RM_FOLDER")
        )

        self.enable_syntax_highlighting = enable_syntax_highlighting

        # Initialize syntax highlighting service if enabled
        if self.enable_syntax_highlighting:
            try:
                from inklink.services.syntax_highlight_compiler import (
                    SyntaxHighlightCompiler,
                )

                self.syntax_compiler = SyntaxHighlightCompiler()
                logger.info("Syntax highlighting enabled")
            except ImportError:
                logger.warning("Syntax highlighting not available")
                self.syntax_compiler = None
                self.enable_syntax_highlighting = False

    @retry(max_attempts=3, delay=1.0)
    def process_code_query(
        self, rm_file_path: str, session_id: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Process a handwritten code query from an .rm file.

        Args:
            rm_file_path: Path to .rm file with handwritten query
            session_id: Optional session ID for conversation context

        Returns:
            Tuple of (success, result dictionary)
        """
        try:
            logger.info(f"Processing code query from {rm_file_path}")

            # Step 1: Recognize handwriting with code detection
            recognition_result = self.handwriting_service.process_ink_with_routing(
                file_path=rm_file_path, session_id=session_id
            )

            if not recognition_result.get("success", False):
                return False, {
                    "error": f"Recognition failed: {recognition_result.get('error')}"
                }

            # Step 2: Check if code content was detected
            routing = recognition_result.get("routing", {})
            if not routing.get("is_code_content"):
                return False, {"error": "No code content detected in handwriting"}

            # Step 3: Get code generation results
            service_results = recognition_result.get("service_results", {})
            code_gen_result = service_results.get("generate_code", {})

            if not code_gen_result.get("success"):
                # If no code generation was triggered, manually trigger it
                code_gen_result = self._generate_code_from_recognition(
                    recognition_result
                )

            if not code_gen_result.get("success"):
                return False, {
                    "error": f"Code generation failed: {code_gen_result.get('error')}"
                }

            # Step 4: Format the response
            response_content = self._format_code_response(
                recognition_result, code_gen_result
            )

            # Step 5: Create .rm document
            rm_path = self._create_code_document(response_content)

            if not rm_path:
                return False, {"error": "Failed to create response document"}

            # Step 6: Upload to reMarkable
            title = f"Code Response - {int(time.time())}"
            success, message = self.remarkable_service.upload(rm_path, title)

            if not success:
                return False, {"error": f"Upload failed: {message}"}

            return True, {
                "recognized_text": recognition_result.get("text", ""),
                "code_detection": recognition_result.get("code_detection", {}),
                "generated_code": code_gen_result.get("code", ""),
                "document_path": rm_path,
                "upload_message": message,
            }

        except Exception as e:
            logger.error(f"Error in ink-to-code processing: {e}", exc_info=True)
            return False, {"error": f"Processing failed: {str(e)}"}

    def _generate_code_from_recognition(
        self, recognition_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate code from recognition results.

        Args:
            recognition_result: Handwriting recognition results

        Returns:
            Code generation results
        """
        text = recognition_result.get("text", "")
        code_blocks = recognition_result.get("code_blocks", [])

        # Use the first code block or the full text
        prompt = code_blocks[0]["cleaned_content"] if code_blocks else text

        # Determine the language hint
        language = None
        if code_blocks and code_blocks[0].get("language") != "generic":
            language = code_blocks[0].get("language")

        # Generate code through LLM manager
        return self.llm_manager.route_task(
            task_type="code_generation", content=prompt, language=language
        )

    def _format_code_response(
        self, recognition_result: Dict[str, Any], code_gen_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format the code generation response for display.

        Args:
            recognition_result: Original recognition results
            code_gen_result: Code generation results

        Returns:
            Formatted content for document creation
        """
        original_text = recognition_result.get("text", "")
        generated_code = code_gen_result.get("code", "")
        language = code_gen_result.get("language", "python")
        explanation = code_gen_result.get("explanation", "")

        # Build structured content
        structured_content = [
            {"type": "h1", "content": "Code Generation Response"},
            {"type": "h2", "content": "Your Request"},
            {"type": "paragraph", "content": original_text},
            {"type": "h2", "content": "Generated Code"},
        ]

        # Add code with syntax highlighting if available
        if self.enable_syntax_highlighting and self.syntax_compiler:
            try:
                highlighted_strokes = self.syntax_compiler.compile_code_to_strokes(
                    generated_code, language
                )
                structured_content.append(
                    {"type": "ink", "strokes": highlighted_strokes}
                )
            except Exception as e:
                logger.warning(f"Syntax highlighting failed: {e}")
                structured_content.append({"type": "code", "content": generated_code})
        else:
            structured_content.append({"type": "code", "content": generated_code})

        # Add explanation if provided
        if explanation:
            structured_content.extend(
                [
                    {"type": "h2", "content": "Explanation"},
                    {"type": "paragraph", "content": explanation},
                ]
            )

        # Add metadata
        metadata = {
            "detected_language": language,
            "code_confidence": recognition_result.get("code_detection", {}).get(
                "confidence", 0.0
            ),
            "tags": recognition_result.get("code_detection", {}).get("tags", []),
        }

        return {
            "title": "Code Generation Response",
            "structured_content": structured_content,
            "metadata": metadata,
        }

    def _create_code_document(self, content: Dict[str, Any]) -> Optional[str]:
        """
        Create a .rm document with the formatted code response.

        Args:
            content: Formatted content dictionary

        Returns:
            Path to created .rm file or None
        """
        try:
            # Generate unique filename
            timestamp = int(time.time() * 1000)
            filename = f"code_response_{timestamp}"

            # Create the document
            rm_path = self.document_service.create_rmdoc_from_content(
                url="", qr_path="", content=content
            )

            if rm_path and os.path.exists(rm_path):
                # Rename to our preferred filename
                new_path = os.path.join(self.temp_dir, f"{filename}.rm")
                os.rename(rm_path, new_path)
                return new_path

            return rm_path

        except Exception as e:
            logger.error(f"Error creating code document: {e}")
            return None

    def process_notebook_pages(
        self, page_files: List[str], notebook_id: str
    ) -> Dict[str, Any]:
        """
        Process multiple pages from a notebook for code content.

        Args:
            page_files: List of .rm file paths
            notebook_id: ID of the notebook for context

        Returns:
            Processing results for all pages
        """
        results = {"pages": [], "code_pages": [], "total_generated": 0}

        for i, page_file in enumerate(page_files):
            logger.info(f"Processing page {i + 1}/{len(page_files)}: {page_file}")

            # Process each page
            success, page_result = self.process_code_query(
                page_file, session_id=notebook_id
            )

            if success and page_result.get("code_detection", {}).get("is_code"):
                results["code_pages"].append(
                    {"page_index": i, "file": page_file, "result": page_result}
                )
                results["total_generated"] += 1

            results["pages"].append(
                {
                    "page_index": i,
                    "file": page_file,
                    "success": success,
                    "result": page_result,
                }
            )

        return results

    def create_combined_response(
        self, pages_results: List[Dict[str, Any]], notebook_name: str
    ) -> Optional[str]:
        """
        Create a combined response document for multiple code pages.

        Args:
            pages_results: Results from processing multiple pages
            notebook_name: Name of the original notebook

        Returns:
            Path to created .rm file or None
        """
        try:
            structured_content = [
                {"type": "h1", "content": f"Code Generation Results - {notebook_name}"},
                {
                    "type": "paragraph",
                    "content": f"Generated {len(pages_results)} code responses",
                },
            ]

            for i, page_result in enumerate(pages_results):
                result = page_result["result"]
                structured_content.extend(
                    [
                        {
                            "type": "h2",
                            "content": f"Page {page_result['page_index'] + 1}",
                        },
                        {
                            "type": "paragraph",
                            "content": result.get("recognized_text", ""),
                        },
                        {"type": "h3", "content": "Generated Code"},
                        {
                            "type": "code",
                            "content": result.get("generated_code", ""),
                        },
                    ]
                )

            content = {
                "title": f"Code Responses - {notebook_name}",
                "structured_content": structured_content,
            }

            return self._create_code_document(content)

        except Exception as e:
            logger.error(f"Error creating combined response: {e}")
            return None
