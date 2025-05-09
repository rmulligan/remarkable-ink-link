"""Handwriting recognition service using MyScript iink SDK."""

from typing import List, Dict, Any, Optional, Tuple
import os
import logging
import time
import re

from inklink.services.interfaces import IHandwritingRecognitionService
from inklink.adapters.handwriting_adapter import HandwritingAdapter
from inklink.utils import format_error
from inklink.config import CONFIG

logger = logging.getLogger(__name__)


class HandwritingRecognitionService(IHandwritingRecognitionService):
    """
    Service for handwriting recognition using MyScript iink SDK.
    Uses the HandwritingAdapter to interact with MyScript and rmscene.
    """

    def __init__(
        self,
        application_key: Optional[str] = None,
        hmac_key: Optional[str] = None,
        handwriting_adapter: Optional[HandwritingAdapter] = None,
    ):
        """
        Initialize the handwriting recognition service.

        Args:
            application_key: Optional application key for MyScript API
            hmac_key: Optional HMAC key for MyScript API
            handwriting_adapter: Optional pre-configured adapter
        """
        # Get API keys from environment variables or config
        self.application_key = (
            application_key
            or os.environ.get("MYSCRIPT_APP_KEY")
            or CONFIG.get("MYSCRIPT_APP_KEY", "")
        )
        self.hmac_key = (
            hmac_key
            or os.environ.get("MYSCRIPT_HMAC_KEY")
            or CONFIG.get("MYSCRIPT_HMAC_KEY", "")
        )

        # Use provided adapter or create a new one
        self.adapter = handwriting_adapter or HandwritingAdapter(
            application_key=self.application_key, hmac_key=self.hmac_key
        )

        if not self.application_key or not self.hmac_key:
            logger.warning(
                "MyScript keys not provided; handwriting recognition not available"
            )

    def classify_region(self, strokes: List[Dict[str, Any]]) -> str:
        """
        Classify a region as 'text', 'math', or 'diagram' based on stroke features.
        Uses simple heuristics (to be replaced with ML or SDK logic).

        Args:
            strokes: List of stroke dictionaries

        Returns:
            Content type classification ("Text", "Math", or "Diagram")
        """
        # Example heuristic: very basic, for demonstration
        if strokes:
            # If many strokes and some are long, guess diagram
            if any(len(s.get("x", [])) > 10 for s in strokes):
                return "Diagram"
            # If strokes are dense and short, guess math
            if len(strokes) > 5:
                return "Math"
        return "Text"

    def initialize_iink_sdk(self, application_key: str, hmac_key: str) -> bool:
        """
        Initialize the MyScript iink SDK with authentication keys.

        Args:
            application_key: Application key for MyScript API
            hmac_key: HMAC key for MyScript API

        Returns:
            True if initialized successfully, False otherwise
        """
        try:
            self.application_key = application_key
            self.hmac_key = hmac_key

            # Use the adapter to initialize the SDK
            success = self.adapter.initialize_sdk(application_key, hmac_key)

            if success:
                logger.info("MyScript iink SDK initialized successfully")
            else:
                logger.error("Failed to initialize MyScript iink SDK")

            return success

        except Exception as e:
            logger.error(f"Error initializing MyScript iink SDK: {e}")
            return False

    def extract_strokes(self, rm_file_path: str) -> List[Dict[str, Any]]:
        """
        Extract strokes from a reMarkable file.

        Args:
            rm_file_path: Path to .rm file

        Returns:
            List of stroke dictionaries
        """
        try:
            # Use the adapter to extract strokes
            strokes = self.adapter.extract_strokes_from_rm_file(rm_file_path)

            if strokes:
                logger.info(f"Extracted {len(strokes)} strokes from {rm_file_path}")
            else:
                logger.warning(f"No strokes extracted from {rm_file_path}")

            return strokes

        except Exception as e:
            logger.error(f"Error extracting strokes from {rm_file_path}: {e}")
            return []

    def convert_to_iink_format(self, strokes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convert reMarkable strokes to iink SDK compatible format.

        Args:
            strokes: List of stroke dictionaries

        Returns:
            Formatted data for iink SDK
        """
        try:
            # Use the adapter to convert strokes to iink format
            iink_data = self.adapter.convert_to_iink_format(strokes)

            # If the adapter didn't return strokes in the right format,
            # fall back to a simple format that works with the API
            if not iink_data or not iink_data.get("strokes"):
                iink_data = {
                    "type": "inkData",
                    "width": CONFIG.get("PAGE_WIDTH", 1872),
                    "height": CONFIG.get("PAGE_HEIGHT", 2404),
                    "strokes": strokes,
                }

            return iink_data

        except Exception as e:
            logger.error(f"Error converting strokes to iink format: {e}")
            return {"type": "inkData", "strokes": []}

    def recognize_handwriting(
        self,
        iink_data: Dict[str, Any],
        content_type: str = "Text",
        language: str = "en_US",
    ) -> Dict[str, Any]:
        """
        Process ink data through the iink SDK and return recognition results.

        Args:
            iink_data: Ink data in iink format
            content_type: Content type (Text, Diagram, Math, etc.)
            language: Language code

        Returns:
            Recognition results
        """
        try:
            if not self.application_key or not self.hmac_key:
                raise ValueError(
                    "MyScript keys not available; cannot recognize handwriting"
                )

            # Use the adapter to recognize handwriting
            result = self.adapter.recognize_handwriting(
                iink_data, content_type, language
            )

            # Handle error cases
            if "error" in result:
                logger.error(f"Recognition failed: {result['error']}")
                return {
                    "success": False,
                    "error": result["error"],
                }

            # Format the result for consistency
            return {
                "success": True,
                "content_id": result.get("id", ""),
                "raw_result": result,
            }

        except Exception as e:
            error_msg = format_error("recognition", "Handwriting recognition failed", e)
            logger.error(error_msg)
            return {"success": False, "error": str(e)}

    def export_content(
        self, content_id: str, format_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Export recognized content in the specified format.

        Args:
            content_id: Content ID from recognition result
            format_type: Format type (text, JIIX, etc.)

        Returns:
            Exported content
        """
        try:
            if not self.application_key or not self.hmac_key:
                raise ValueError("MyScript keys not available; cannot export content")

            # Use the adapter to export content
            result = self.adapter.export_content(content_id, format_type)

            # Handle error cases
            if "error" in result:
                logger.error(f"Export failed: {result['error']}")
                return {"success": False, "error": result["error"]}

            logger.info(f"Export successful: {format_type}")
            return {"success": True, "content": result}

        except Exception as e:
            error_msg = format_error("export", "Content export failed", e)
            logger.error(error_msg)
            return {"success": False, "error": str(e)}

    def recognize_from_ink(
        self,
        ink_data: Optional[bytes] = None,
        file_path: Optional[str] = None,
        content_type: Optional[str] = None,
        language: str = "en_US",
    ) -> Dict[str, Any]:
        """
        High-level method: Accepts ink data or file path, extracts strokes, classifies region,
        recognizes handwriting, and returns result.
        If content_type is None or 'auto', classify region automatically.

        Args:
            ink_data: Binary ink data
            file_path: Path to .rm file
            content_type: Content type (Text, Diagram, Math) or 'auto'
            language: Language code

        Returns:
            Recognition results
        """
        try:
            # Handle the case where ink_data is provided (save to temp file)
            if ink_data is not None:
                import tempfile

                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".rm"
                ) as temp_file:
                    temp_file.write(ink_data)
                    temp_path = temp_file.name

                try:
                    # Extract strokes from temp file
                    strokes = self.extract_strokes(rm_file_path=temp_path)
                finally:
                    # Clean up the temporary file
                    try:
                        import os

                        os.unlink(temp_path)
                    except Exception:
                        pass
            elif file_path is not None:
                # Extract strokes from provided file path
                strokes = self.extract_strokes(rm_file_path=file_path)
            else:
                raise ValueError("Either ink_data or file_path must be provided")

            # Auto-classify content type if needed
            if content_type is None or content_type.lower() == "auto":
                content_type = self.classify_region(strokes)

            # Convert strokes to iink format
            iink_data = self.convert_to_iink_format(strokes)

            # Use the adapter to recognize handwriting
            result = self.recognize_handwriting(iink_data, content_type, language)
            return result

        except Exception as e:
            logger.error(f"Handwriting recognition pipeline failed: {e}")
            return {"success": False, "error": str(e)}

    def recognize_multi_page_ink(
        self,
        page_files: List[str],
        language: str = "en_US",
        user_links: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Recognize handwriting from multiple page files, maintaining per-page and cross-page context.

        Args:
            page_files: List of file paths, each representing a handwritten page
            language: Language code for recognition
            user_links: Optional user-defined cross-page links, e.g.,
                [{"from_page": 1, "to_page": 2, "type": "reference", "label": "See Figure 1"}]

        Returns:
            Structured content with per-page items and cross-page links:
                {
                    "pages": [...],
                    "cross_page_links": [...]
                }
        """
        structured_pages = []
        cross_page_links = user_links[:] if user_links else []

        for i, file_path in enumerate(page_files):
            # Extract strokes from file
            strokes = self.extract_strokes(rm_file_path=file_path)

            # Classify content type
            content_type = self.classify_region(strokes)

            # Convert to iink format
            iink_data = self.convert_to_iink_format(strokes)

            # Recognize handwriting
            result = self.recognize_handwriting(iink_data, content_type, language)

            if result.get("success"):
                # Extract from API format
                result = result.get("raw_result", {})

            items = []
            page_references = []

            # Extract recognized text and look for references
            if "text" in result:
                text = result["text"]
                items.append({"type": content_type.lower(), "content": text})

                # Simple automatic cross-page reference extraction (e.g., "see page X")
                ref_matches = re.findall(
                    r"(see|refer to) page (\d+)", text, re.IGNORECASE
                )
                for _, ref_page in ref_matches:
                    ref_page_num = int(ref_page)
                    if 1 <= ref_page_num <= len(page_files) and ref_page_num != (i + 1):
                        link = {
                            "from_page": i + 1,
                            "to_page": ref_page_num,
                            "type": "auto_reference",
                            "label": f"Reference to page {ref_page_num}",
                        }
                        cross_page_links.append(link)
                        page_references.append(link)

            structured_pages.append(
                {
                    "page_number": i + 1,
                    "items": items,
                    "metadata": {"references": page_references},
                }
            )

        # Remove duplicate links (by from_page, to_page, type, label)
        seen = set()
        unique_links = []
        for link in cross_page_links:
            key = (
                link["from_page"],
                link["to_page"],
                link.get("type"),
                link.get("label"),
            )
            if key not in seen:
                unique_links.append(link)
                seen.add(key)

        return {
            "pages": structured_pages,
            "cross_page_links": unique_links,
        }
