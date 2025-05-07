"""Handwriting recognition service using MyScript iink SDK."""

from typing import List, Dict, Any, Optional
import os
import logging
import json
import hmac
import hashlib
import base64
import time
import requests
from urllib.parse import urljoin

# Import rmscene for .rm file parsing
import rmscene

from inklink.services.interfaces import IHandwritingRecognitionService
from inklink.utils import retry_operation, format_error
from inklink.config import CONFIG

logger = logging.getLogger(__name__)


class HandwritingRecognitionService(IHandwritingRecognitionService):
    """
    Service for handwriting recognition using MyScript iink SDK.
    Integrates both rmscene and MyScript for handwriting recognition.
    """

    # MyScript iink SDK API endpoints
    IINK_BASE_URL = "https://cloud.myscript.com/api/v4.0/"
    RECOGNITION_ENDPOINT = "iink/recognition"
    EXPORT_ENDPOINT = "iink/export"

    def __init__(
        self,
        application_key: Optional[str] = None,
        hmac_key: Optional[str] = None,
        rmscene_adapter: Optional[Any] = None,
        myscript_adapter: Optional[Any] = None,
    ):
        # Adapters for testability/extensibility
        self.rmscene = rmscene_adapter or rmscene
        self.myscript = myscript_adapter
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

        if not self.application_key or not self.hmac_key:
            logger.warning(
                "MyScript keys not provided; handwriting recognition not available"
            )

    def classify_region(self, strokes: List[Dict[str, Any]]) -> str:
        """
        Classify a region as 'text', 'math', or 'diagram' based on stroke features.
        Placeholder: Uses simple heuristics (to be replaced with ML or SDK logic).
        """
        # Example heuristic: very basic, for demonstration
        if len(strokes) > 0:
            # If many strokes and some are long, guess diagram
            if any(len(s.get("x", [])) > 10 for s in strokes):
                return "Diagram"
            # If strokes are dense and short, guess math
            if len(strokes) > 5:
                return "Math"
        return "Text"

    def initialize_iink_sdk(self, application_key: str, hmac_key: str) -> bool:
        """Initialize the MyScript iink SDK with authentication keys."""
        try:
            self.application_key = application_key
            self.hmac_key = hmac_key

            # Validate keys by making a simple test request
            test_data = {"type": "configuration", "configuration": {"lang": "en_US"}}
            headers = self._generate_headers(test_data)
            response = requests.post(
                urljoin(self.IINK_BASE_URL, "iink/configuration"),
                json=test_data,
                headers=headers,
            )
            if response.status_code == 200:
                logger.info("MyScript iink SDK initialized successfully")
                return True
            else:
                logger.error(f"Failed to initialize MyScript iink SDK: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error initializing MyScript iink SDK: {e}")
            return False

    def extract_strokes(self, rm_file_path: str) -> List[Dict[str, Any]]:
        """Extract strokes from a reMarkable file."""
        try:
            # Use rmscene to parse the .rm file
            scene = self.rmscene.load(rm_file_path)
            strokes = []
            for layer in scene.layers:
                for line in layer.lines:
                    stroke = {
                        "id": str(len(strokes)),
                        "x": [point.x for point in line.points],
                        "y": [point.y for point in line.points],
                        "pressure": [point.pressure for point in line.points],
                        "timestamp": int(time.time() * 1000),
                    }
                    strokes.append(stroke)
            logger.info(f"Extracted {len(strokes)} strokes from {rm_file_path}")
            return strokes
        except Exception as e:
            logger.error(f"Error extracting strokes from {rm_file_path}: {e}")
            return []

    def convert_to_iink_format(self, strokes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert reMarkable strokes to iink SDK compatible format."""
        try:
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
        """Process ink data through the iink SDK and return recognition results."""
        try:
            if not self.application_key or not self.hmac_key:
                raise ValueError(
                    "MyScript keys not available; cannot recognize handwriting"
                )
            request_data = {
                "configuration": {
                    "lang": language,
                    "contentType": content_type,
                    "recognition": {
                        "text": {"guides": {"enable": False}, "smartGuide": False}
                    },
                },
                **iink_data,
            }
            headers = self._generate_headers(request_data)
            response = requests.post(
                urljoin(self.IINK_BASE_URL, self.RECOGNITION_ENDPOINT),
                json=request_data,
                headers=headers,
            )
            if response.status_code != 200:
                logger.error(
                    f"Recognition failed: {response.status_code} - {response.text}"
                )
                return {
                    "success": False,
                    "error": f"Recognition failed: {response.text}",
                }
            result = response.json()
            logger.info(f"Recognition successful: {result.get('id')}")
            return {
                "success": True,
                "content_id": result.get("id"),
                "raw_result": result,
            }
        except Exception as e:
            error_msg = format_error("recognition", "Handwriting recognition failed", e)
            logger.error(error_msg)
            return {"success": False, "error": str(e)}

    def export_content(
        self, content_id: str, format_type: str = "text"
    ) -> Dict[str, Any]:
        """Export recognized content in the specified format."""
        try:
            if not self.application_key or not self.hmac_key:
                raise ValueError("MyScript keys not available; cannot export content")
            request_data = {"format": format_type}
            headers = self._generate_headers(request_data)
            export_url = (
                f"{urljoin(self.IINK_BASE_URL, self.EXPORT_ENDPOINT)}/{content_id}"
            )
            response = requests.post(export_url, json=request_data, headers=headers)
            if response.status_code != 200:
                logger.error(f"Export failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"Export failed: {response.text}"}
            result = response.json()
            logger.info(f"Export successful: {format_type}")
            return {"success": True, "content": result}
        except Exception as e:
            error_msg = format_error("export", "Content export failed", e)
            logger.error(error_msg)
            return {"success": False, "error": str(e)}

    def recognize_from_ink(
        self,
        ink_data: bytes = None,
        file_path: str = None,
        content_type: str = None,
        language: str = "en_US",
    ) -> Dict[str, Any]:
        """
        High-level method: Accepts ink data or file path, extracts strokes, classifies region, recognizes handwriting, and returns result.
        If content_type is None or 'auto', classify region automatically.
        """
        try:
            if ink_data is not None:
                strokes = self.rmscene.extract_strokes(ink_data=ink_data)
            elif file_path is not None:
                strokes = self.extract_strokes(file_path)
            else:
                raise ValueError("Either ink_data or file_path must be provided")
            if content_type is None or content_type.lower() == "auto":
                content_type = self.classify_region(strokes)
            iink_data = self.convert_to_iink_format(strokes)
            # Support both direct API call and adapter patterns
            if hasattr(self.myscript, "recognize"):
                # Use adapter if provided
                result = self.myscript.recognize(iink_data, content_type, language)
                return result
            else:
                # Otherwise use direct API
                return self.recognize_handwriting(iink_data, content_type, language)
        except Exception as e:
            logger.error(f"Handwriting recognition pipeline failed: {e}")
            return {"error": str(e)}

    def recognize_multi_page_ink(
        self,
        page_files: List[str],
        language: str = "en_US",
        user_links: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Recognize handwriting from multiple page files, maintaining per-page and cross-page context.

        Args:
            page_files (List[str]): List of file paths, each representing a handwritten page.
            language (str): Language code for recognition.
            user_links (Optional[List[Dict[str, Any]]]): Optional user-defined cross-page links, e.g.,
                [{"from_page": 1, "to_page": 2, "type": "reference", "label": "See Figure 1"}]

        Returns:
            Dict[str, Any]: Structured content with per-page items and cross-page links.
                {
                    "pages": [...],
                    "cross_page_links": [...]
                }
        """
        structured_pages = []
        cross_page_links = user_links[:] if user_links else []

        for i, file_path in enumerate(page_files):
            strokes = self.extract_strokes(rm_file_path=file_path)
            content_type = self.classify_region(strokes)
            iink_data = self.convert_to_iink_format(strokes)
            
            # Support both direct API call and adapter patterns
            if hasattr(self.myscript, 'recognize'):
                result = self.myscript.recognize(iink_data, content_type, language)
            else:
                result = self.recognize_handwriting(iink_data, content_type, language)
                if result.get('success'):
                    # Extract from API format
                    result = result.get('raw_result', {})

            items = []
            page_references = []

            # Example: extract recognized items and look for references
            if "text" in result:
                text = result["text"]
                items.append({"type": content_type.lower(), "content": text})

                # Simple automatic cross-page reference extraction (e.g., "see page X")
                import re

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

    def _generate_headers(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Generate headers with HMAC authentication for MyScript API."""
        if not self.hmac_key:
            raise ValueError("HMAC key is missing or empty, cannot generate headers")
        data_json = json.dumps(data, sort_keys=True)
        timestamp = str(int(time.time() * 1000))
        message = timestamp + data_json
        signature_bytes = hmac.new(
            self.hmac_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha512
        ).digest()
        signature = base64.b64encode(signature_bytes).decode("utf-8")
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "applicationKey": self.application_key,
            "hmac": signature,
            "timestamp": timestamp,
        }
