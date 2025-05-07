"""Handwriting recognition service using MyScript iink SDK."""

from typing import List, Dict, Any, Optional, Union
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
from rmscene import scene_stream

from inklink.services.interfaces import IHandwritingRecognitionService
from inklink.utils import retry_operation, format_error
from inklink.config import CONFIG

logger = logging.getLogger(__name__)


class RmsceneAdapter:
    """
    Adapter for rmscene tool to extract stroke data from ink files.
    This class should be replaced or mocked in tests.
    """

    def extract_strokes(
        self,
        file_path: Optional[str] = None,
        ink_data: Optional[bytes] = None
    ) -> List[Dict[str, Any]]:
        """Extract stroke data from .rm file or raw ink data.
        
        Args:
            file_path: Path to .rm file
            ink_data: Raw ink data bytes
            
        Returns:
            List of stroke dictionaries with x, y coordinates
        """
        try:
            if file_path:
                # If we have a file path, use the actual rmscene library
                with open(file_path, 'rb') as f:
                    # Use the correct rmscene API to load the file
                    blocks = scene_stream.read_blocks(f)
                    scene = []
                    for block in blocks:
                        if isinstance(block, scene_stream.SceneItemBlock):
                            scene.append(block)
                
                # Now process the scene blocks to extract strokes
                strokes = []
                for item in scene:
                    if hasattr(item, 'points') and item.points:
                        stroke = {
                            "points": [(p.x, p.y) for p in item.points],
                            "width": getattr(item, 'width', 1.0),
                            "color": getattr(item, 'color', 0)
                        }
                        strokes.append(stroke)
                
                return strokes
            elif ink_data:
                # For raw bytes, we'd need to implement a way to parse them
                # This could use in-memory parsing with rmscene if supported
                # For now, falling back to a placeholder implementation
                logger.warning("Direct ink_data processing not fully implemented")
                return [{"x": [0, 1], "y": [0, 1]}]
            else:
                raise ValueError(
                    "No ink data or file path provided to rmscene adapter."
                )
        except Exception as e:
            logging.error(f"Rmscene extraction failed: {e}")
            raise


class MyScriptAdapter:
    """
    Adapter for MyScript SDK/API to perform handwriting recognition.
    This class should be replaced or mocked in tests.
    """

    # MyScript iink SDK API endpoints
    IINK_BASE_URL = "https://cloud.myscript.com/api/v4.0/"
    RECOGNITION_ENDPOINT = "iink/recognition"
    EXPORT_ENDPOINT = "iink/export"

    def __init__(self):
        self.initialized = False
        self.application_key = None
        self.hmac_key = None

    def initialize(self, application_key: str, hmac_key: str) -> bool:
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
                timeout=10,
            )
            if response.status_code == 200:
                logger.info("MyScript iink SDK initialized successfully")
                self.initialized = True
                return True
            else:
                logger.error(f"Failed to initialize MyScript iink SDK: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error initializing MyScript iink SDK: {e}")
            return False

    def recognize(
        self,
        iink_data: Dict[str, Any],
        content_type: str = "Text",
        language: str = "en_US",
    ) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("MyScript SDK not initialized.")

        try:
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

    def export(self, content_id: str, format_type: str = "text") -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("MyScript SDK not initialized.")

        try:
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

    def _generate_headers(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Generate headers with HMAC authentication for MyScript API."""
        if not self.application_key or not self.hmac_key:
            raise ValueError(
                "API or HMAC key is missing or empty, cannot generate headers"
            )

        data_json = json.dumps(data, sort_keys=True)
        timestamp = str(int(time.time() * 1000))
        message = timestamp + data_json
        signature_bytes = hmac.new(
            self.hmac_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha512
        ).digest()
        signature = base64.b64encode(signature_bytes).decode("utf-8")

        # Ensure we never pass None values in the headers
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "applicationKey": str(self.application_key),
            "hmac": signature,
            "timestamp": timestamp,
        }


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
        rmscene_adapter: Optional[RmsceneAdapter] = None,
        myscript_adapter: Optional[MyScriptAdapter] = None,
    ):
        # Adapters for testability/extensibility
        self.rmscene = rmscene_adapter or RmsceneAdapter()
        self.myscript = myscript_adapter or MyScriptAdapter()
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
        else:
            # Initialize the MyScript adapter
            self.myscript.initialize(self.application_key, self.hmac_key)

    def classify_region(self, strokes: List[Dict[str, Any]]) -> str:
        """
        Classify a region as 'text', 'math', or 'diagram' based on stroke features.
        Placeholder: Uses simple heuristics (to be replaced with ML or SDK logic).
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
        """Initialize the MyScript iink SDK with authentication keys."""
        self.application_key = application_key
        self.hmac_key = hmac_key
        return self.myscript.initialize(application_key, hmac_key)

    def extract_strokes(self, rm_file_path: str) -> List[Dict[str, Any]]:
        """Extract strokes from a reMarkable file."""
        return self.rmscene.extract_strokes(file_path=rm_file_path)

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
        return self.myscript.recognize(iink_data, content_type, language)

    def export_content(
        self, content_id: str, format_type: str = "text"
    ) -> Dict[str, Any]:
        """Export recognized content in the specified format."""
        return self.myscript.export(content_id, format_type)

    def recognize_from_ink(
        self,
        ink_data: Optional[bytes] = None,
        file_path: Optional[str] = None,
        content_type: Optional[str] = None,
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
                strokes = self.rmscene.extract_strokes(file_path=file_path)
            else:
                raise ValueError("Either ink_data or file_path must be provided")

            if content_type is None or content_type.lower() == "auto":
                content_type = self.classify_region(strokes)
            iink_data = self.convert_to_iink_format(strokes)
            result = self.recognize_handwriting(iink_data, content_type, language)
            return result
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

        # Dictionary to store detected references for linking
        detected_references = {}

        for i, file_path in enumerate(page_files):
            strokes = self.extract_strokes(file_path)
            content_type = self.classify_region(strokes)
            iink_data = self.convert_to_iink_format(strokes)
            result = self.recognize_handwriting(iink_data, content_type, language)

            items = []
            page_references = []

            # Extract recognized items and look for references
            if result.get("success", False) and "raw_result" in result:
                text = result["raw_result"].get("text", "")
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

                        # Store this reference in our tracking dictionary
                        if i + 1 not in detected_references:
                            detected_references[i + 1] = []
                        detected_references[i + 1].append(ref_page_num)

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
