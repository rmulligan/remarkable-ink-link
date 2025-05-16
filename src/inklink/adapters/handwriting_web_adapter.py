"""Handwriting recognition web adapter for InkLink.

This module provides an adapter for handwriting recognition using the
MyScript Web API instead of the local SDK.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests

from inklink.adapters.adapter import Adapter

logger = logging.getLogger(__name__)

# MyScript API configuration
API_BASE_URL = "https://cloud.myscript.com/api/v4.0/iink/"
RECOGNITION_ENDPOINT = (
    "batch"  # Changed from "recognize" to "batch" based on successful curl request
)


class HandwritingWebAdapter(Adapter):
    """Adapter for MyScript Web API for handwriting recognition."""

    def __init__(self, application_key: str = None, hmac_key: str = None):
        """
        Initialize with API keys.

        Args:
            application_key: Application key for MyScript API
            hmac_key: HMAC key for MyScript API
        """
        self.application_key = application_key
        self.hmac_key = hmac_key
        self.initialized = bool(application_key and hmac_key)

    def ping(self) -> bool:
        """
        Check if the handwriting recognition service is available.

        Returns:
            True if API keys are available, False otherwise
        """
        if not self.application_key or not self.hmac_key:
            return False

        # Perform a lightweight request to the API to check if it's accessible
        try:
            # Use a minimal request to test connectivity
            current_time = int(time.time() * 1000)

            # Create request payload in the updated format
            request_data = {
                "contentType": "Text",
                "strokes": [
                    {
                        "id": "test-stroke",
                        "x": [100],
                        "y": [100],
                        "t": [current_time],
                        "p": [0.5],
                    }
                ],
                "scaleX": 0.265,
                "scaleY": 0.265,
            }

            # Generate HMAC signature
            request_json = json.dumps(request_data)
            hmac_signature = self._generate_hmac(request_json)

            # Set up headers per MyScript authentication requirements based on successful curl request
            headers = {
                "Accept": "application/json,application/vnd.myscript.jiix",
                "Content-Type": "application/json",
                "applicationkey": self.application_key,  # Lowercase key as seen in the curl request
                "hmac": hmac_signature,
                "origin": "https://cloud.myscript.com",  # Adding additional headers from the curl
                "referer": "https://cloud.myscript.com/",
            }

            # Make the request with a short timeout
            url = urljoin(API_BASE_URL, RECOGNITION_ENDPOINT)
            response = requests.post(
                url,
                headers=headers,
                data=request_json,
                timeout=5,  # Short timeout for ping
            )

            # Check if the request was successful (even if recognition fails)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to ping MyScript Web API: {e}")
            return False

    def _generate_hmac(self, data: str) -> str:
        """
        Generate HMAC signature for request authentication.

        Per the MyScript documentation:
        https://developer.myscript.com/docs/interactive-ink/1.4/web/rest/architecture/#credentials

        The HMAC signature is created by:
        1. Using the HMAC key as the secret
        2. Signing the complete request body
        3. Using SHA-512 algorithm
        4. Base64 encoding the result

        Args:
            data: Data to sign (JSON string of the request body)

        Returns:
            HMAC signature as base64 encoded string
        """
        # Create a new HMAC instance with:
        # - The HMAC key as secret
        # - The request body as message
        # - SHA-512 as the algorithm
        h = hmac.new(
            bytes(self.hmac_key, "utf-8"), data.encode("utf-8"), hashlib.sha512
        )
        # Return the base64 encoded digest
        return base64.b64encode(h.digest()).decode("utf-8")

    def extract_strokes_from_rm_file(self, rm_file_path: str) -> List[Dict[str, Any]]:
        """
        Extract strokes from a reMarkable file.

        Args:
            rm_file_path: Path to .rm file

        Returns:
            List of stroke dictionaries
        """
        try:
            # Import rmscene for parsing .rm files
            try:
                import rmscene
                from rmscene.scene_items import Line
                from rmscene.scene_stream import read_tree
            except ImportError:
                logger.error("rmscene not installed - cannot parse .rm files")
                return []

            # Parse .rm file using current rmscene API (v0.7.0+)
            with open(rm_file_path, "rb") as f:
                try:
                    # Try using the newer rmscene API
                    scene_tree = read_tree(f)

                    # Convert strokes to the format needed for MyScript Web API
                    strokes = []

                    # Find all Line items in the tree
                    for item_id, item in scene_tree.items.items():
                        if isinstance(item, Line):
                            # Extract x, y, pressure and timestamps for each point
                            x_points = []
                            y_points = []
                            pressures = []
                            timestamps = []

                            for point in item.points:
                                x_points.append(point.x)
                                y_points.append(point.y)
                                pressures.append(point.pressure)
                                # Use 't' attribute for timestamp in newer API
                                timestamps.append(point.t if hasattr(point, "t") else 0)

                            # Create stroke in MyScript format
                            stroke = {
                                "id": str(item_id),
                                "x": x_points,
                                "y": y_points,
                                "p": pressures,
                                "t": timestamps,
                                "color": (
                                    str(item.color)
                                    if hasattr(item, "color")
                                    else "#000000"
                                ),
                                "width": (
                                    float(item.pen.value)
                                    if hasattr(item, "pen")
                                    else 2.0
                                ),
                            }

                            strokes.append(stroke)

                    if strokes:
                        logger.info(
                            f"Extracted {len(strokes)} strokes using current rmscene API"
                        )
                        return strokes
                    logger.warning("No strokes found in file using current rmscene API")

                except Exception as scene_tree_error:
                    logger.error(
                        f"Failed to use current rmscene API: {scene_tree_error}"
                    )
                    # Older .rm files might need a different approach
                    logger.warning("Trying fallback extraction method...")
                    return []

            return []

        except Exception as e:
            logger.error(f"Failed to extract strokes from .rm file: {e}")
            return []

    def convert_to_iink_format(self, strokes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convert reMarkable strokes to MyScript Web API compatible format.

        Based on the successful curl request format.

        Args:
            strokes: List of stroke dictionaries from reMarkable

        Returns:
            Formatted data for MyScript Web API
        """
        try:
            # Create the ink data structure matching the successful curl request format
            ink_data = {
                "configuration": {
                    "text": {
                        "guides": {"enable": True},
                        "smartGuide": True,
                        "smartGuideFadeOut": {"enable": False, "duration": 10000},
                        "mimeTypes": ["text/plain", "application/vnd.myscript.jiix"],
                        "margin": {"top": 20, "left": 10, "right": 10},
                        "eraser": {"erase-precisely": False},
                    },
                    "lang": "en_US",
                    "export": {
                        "image-resolution": 300,
                        "jiix": {
                            "bounding-box": False,
                            "strokes": False,
                            "text": {"chars": False, "words": True},
                        },
                    },
                },
                "xDPI": 96,
                "yDPI": 96,
                "contentType": "Text",
                "theme": "ink {\ncolor: #000000;\n-myscript-pen-width: 1;\n-myscript-pen-fill-style: none;\n-myscript-pen-fill-color: #FFFFFF00;\n}\n.math {\nfont-family: STIXGeneral;\n}\n.math-solved {\nfont-family: STIXGeneral;\ncolor: #A8A8A8FF;\n}\n.text {\nfont-family: MyScriptInter;\nfont-size: 10;\n}\n",
                "strokeGroups": [],
                "height": 500,
                "width": 656,
                "conversionState": "DIGITAL_EDIT",
            }

            # Create a stroke group with the strokes
            stroke_group = {
                "penStyle": "color: #000000;\n-myscript-pen-width: 1;",
                "strokes": [],
            }

            # Add strokes to the structure
            for stroke in strokes:
                web_api_stroke = {
                    "x": stroke.get("x", []),
                    "y": stroke.get("y", []),
                    "t": (
                        stroke.get("timestamp", [])
                        if stroke.get("timestamp")
                        else stroke.get("t", [])
                    ),
                    "p": (
                        stroke.get("pressure", [])
                        if stroke.get("pressure")
                        else stroke.get("p", [])
                    ),
                    "pointerType": "pen",  # Default to pen
                }

                # Add stroke to the stroke group
                stroke_group["strokes"].append(web_api_stroke)

            # Add the stroke group to the data
            ink_data["strokeGroups"].append(stroke_group)

            return ink_data

        except Exception as e:
            logger.error(f"Failed to convert to MyScript Web API format: {e}")
            # Return a minimal valid structure if conversion fails
            return {
                "contentType": "Text",
                "xDPI": 96,
                "yDPI": 96,
                "strokeGroups": [{"strokes": []}],
                "height": 500,
                "width": 656,
                "conversionState": "DIGITAL_EDIT",
            }

    def recognize_handwriting(
        self,
        iink_data: Dict[str, Any],
        content_type: str = "Text",
        language: str = "en_US",
    ) -> Dict[str, Any]:
        """
        Process ink data through the MyScript Web API and return recognition results.

        Args:
            iink_data: Ink data in MyScript Web API format
            content_type: Content type (Text, Diagram, Math, etc.)
            language: Language code

        Returns:
            Recognition results
        """
        try:
            # Check if API keys are available
            if not self.application_key or not self.hmac_key:
                logger.error("MyScript API keys not available")
                return {"error": "API keys not available"}

            # Set content type in the request data
            iink_data["contentType"] = content_type

            # Make sure we have the configuration section
            if "configuration" not in iink_data:
                iink_data["configuration"] = {}

            # Set language in configuration
            iink_data["configuration"]["lang"] = language

            # Add content-type specific configuration
            if content_type.lower() == "text":
                if "text" not in iink_data["configuration"]:
                    iink_data["configuration"]["text"] = {}
                if "configuration" not in iink_data["configuration"]["text"]:
                    iink_data["configuration"]["text"]["configuration"] = {}

                iink_data["configuration"]["text"]["configuration"]["addLKText"] = True

            elif content_type.lower() == "math":
                if "math" not in iink_data["configuration"]:
                    iink_data["configuration"]["math"] = {}

                iink_data["configuration"]["math"]["solver"] = {
                    "enable": True,
                    "fractional-part-digits": 3,
                    "decimal-separator": ".",
                }

            elif content_type.lower() == "diagram":
                if "diagram" not in iink_data["configuration"]:
                    iink_data["configuration"]["diagram"] = {}

                iink_data["configuration"]["diagram"]["convert"] = {
                    "types": ["text", "shape"],
                    "matchTextSize": True,
                }

            # Convert to JSON for request
            request_json = json.dumps(iink_data)

            # Generate HMAC signature
            hmac_signature = self._generate_hmac(request_json)

            # Set up headers per MyScript authentication requirements based on successful curl request
            headers = {
                "Accept": "application/json,application/vnd.myscript.jiix",
                "Content-Type": "application/json",
                "applicationkey": self.application_key,  # Lowercase key as seen in the curl request
                "hmac": hmac_signature,
                "origin": "https://cloud.myscript.com",  # Adding additional headers from the curl
                "referer": "https://cloud.myscript.com/",
            }

            # Send request to MyScript Web API
            url = urljoin(API_BASE_URL, RECOGNITION_ENDPOINT)
            logger.info(f"Sending recognition request to {url}")

            response = requests.post(
                url,
                headers=headers,
                data=request_json,
                timeout=30,  # Reasonable timeout for recognition
            )

            # Check response status
            if response.status_code == 200:
                result = response.json()
                logger.info("Recognition successful")

                # Add a consistent ID for compatibility with existing code
                if "id" not in result:
                    result["id"] = f"web-recognition-{int(time.time())}"

                return result
            error_message = f"Recognition failed: HTTP {response.status_code}"
            try:
                error_details = response.json()
                error_message = f"{error_message} - {json.dumps(error_details)}"
            except Exception:
                error_message = f"{error_message} - {response.text}"

            logger.error(error_message)
            return {"error": error_message}

        except Exception as e:
            logger.error(f"Failed to recognize handwriting: {e}")
            return {"error": str(e)}

    def export_content(
        self, content_id: str, format_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Export recognized content in the specified format.

        Note: For the Web API, this is a simplified operation since most formatting
        is handled during the recognition phase.

        Args:
            content_id: Content ID or raw recognition result
            format_type: Format type (text, JIIX, etc.)

        Returns:
            Exported content
        """
        try:
            # If content_id is a string, try to parse it as JSON
            if isinstance(content_id, str):
                try:
                    content = json.loads(content_id)
                except json.JSONDecodeError:
                    # If it's not JSON, return it as is
                    return {"content": content_id, "format": format_type}
            else:
                content = content_id

            # Extract the main recognition result based on format type
            if format_type.lower() == "text":
                if "result" in content:
                    return {"content": content["result"], "format": "text"}
                if "candidates" in content and len(content["candidates"]) > 0:
                    return {"content": content["candidates"][0], "format": "text"}
                # Try to extract text from JIIX or other formats
                return {"content": json.dumps(content), "format": "json"}
            elif format_type.lower() in ["latex", "mathml"] and "result" in content:
                # For math content, extract the specific format
                math_formats = content.get("result", {})
                if format_type.upper() in math_formats:
                    return {
                        "content": math_formats[format_type.upper()],
                        "format": format_type,
                    }
                return {"content": json.dumps(math_formats), "format": "json"}
            else:
                # For other formats, return the full result in JSON
                return {"content": json.dumps(content), "format": "json"}

        except Exception as e:
            logger.error(f"Failed to export content: {e}")
            return {"error": str(e)}

    def process_rm_file(
        self, rm_file_path: str, content_type: str = "Text", language: str = "en_US"
    ) -> Dict[str, Any]:
        """
        Process a reMarkable file and return recognized text.

        Args:
            rm_file_path: Path to .rm file
            content_type: Content type (Text, Diagram, Math, etc.)
            language: Language code

        Returns:
            Recognition results
        """
        try:
            # Check if file exists
            if not os.path.exists(rm_file_path):
                logger.error(f"File not found: {rm_file_path}")
                return {"error": "File not found"}

            # Extract strokes
            strokes = self.extract_strokes_from_rm_file(rm_file_path)

            if not strokes:
                logger.error("No strokes found in file")
                return {"error": "No strokes found"}

            # Convert to MyScript Web API format
            iink_data = self.convert_to_iink_format(strokes)

            if not iink_data or not iink_data.get("strokeGroups", [{}])[0].get(
                "strokes"
            ):
                logger.error("Failed to convert to MyScript Web API format")
                return {"error": "Failed to convert to MyScript Web API format"}

            # Recognize handwriting
            result = self.recognize_handwriting(iink_data, content_type, language)

            return result

        except Exception as e:
            logger.error(f"Failed to process .rm file: {e}")
            return {"error": str(e)}
