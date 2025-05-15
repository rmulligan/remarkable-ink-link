"""Handwriting recognition adapter for InkLink.

This module provides an adapter for handwriting recognition services
like MyScript iink SDK.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from inklink.adapters.adapter import Adapter

logger = logging.getLogger(__name__)


class HandwritingAdapter(Adapter):
    """Adapter for MyScript iink SDK or other handwriting recognition services."""

    def __init__(self, application_key: str = None, hmac_key: str = None):
        """
        Initialize with API keys.

        Args:
            application_key: Application key for MyScript API
            hmac_key: HMAC key for MyScript API
        """
        self.application_key = application_key
        self.hmac_key = hmac_key
        self.initialized = False

        # Initialize SDK if keys provided
        if application_key and hmac_key:
            self.initialize_sdk(application_key, hmac_key)

    def ping(self) -> bool:
        """
        Check if the handwriting recognition service is available.

        Returns:
            True if available and initialized, False otherwise
        """
        return self.initialized

    def initialize_sdk(self, application_key: str, hmac_key: str) -> bool:
        """
        Initialize the MyScript iink SDK with authentication keys.

        Args:
            application_key: Application key for MyScript API
            hmac_key: HMAC key for MyScript API

        Returns:
            True if initialized successfully, False otherwise
        """
        try:
            # Import here to handle case where MyScript SDK is not installed
            try:
                from iink.iink import IInkConfiguration, InkModel
            except ImportError:
                logger.warning("MyScript iink SDK not installed")
                return False

            # Initialize SDK
            configuration = IInkConfiguration()
            configuration.setStringProperty("configuration-manager.search-path", ".")
            configuration.setStringProperty(
                "configuration-manager.application-key", application_key
            )
            configuration.setStringProperty("configuration-manager.hmac-key", hmac_key)
            configuration.setStringProperty("content-package.temp-directory", ".")

            # Check if initialization is successful
            try:
                # Create a test model to check if SDK is initialized correctly
                InkModel()  # Just instantiate to check if it works
                self.initialized = True
                self.application_key = application_key
                self.hmac_key = hmac_key
                logger.info("MyScript iink SDK initialized successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to create ink model: {e}")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize MyScript iink SDK: {e}")
            return False

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
            except ImportError:
                logger.error("rmscene not installed - cannot parse .rm files")
                return []

            # Parse .rm file
            with open(rm_file_path, "rb") as f:
                scene = rmscene.Scene.from_bytes(f.read())

            # Convert strokes to the format needed for iink SDK
            strokes = []
            for layer in scene.layers:
                for line in layer.lines:
                    stroke = {
                        "points": [],
                        "width": line.width,
                        "color": line.color,
                        "timestamp": line.timestamp_ms,
                    }

                    # Convert points
                    for point in line.points:
                        stroke["points"].append(
                            {
                                "x": point.x,
                                "y": point.y,
                                "pressure": point.pressure,
                                "timestamp": point.timestamp_ms,
                            }
                        )

                    strokes.append(stroke)

            return strokes

        except Exception as e:
            logger.error(f"Failed to extract strokes from .rm file: {e}")
            return []

    def convert_to_iink_format(self, strokes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convert reMarkable strokes to iink SDK compatible format.

        Args:
            strokes: List of stroke dictionaries from reMarkable

        Returns:
            Formatted data for iink SDK
        """
        try:
            # Import MyScript SDK
            try:
                from iink.iink import InkModel, InkStroke, Point, PointerEventType
            except ImportError:
                logger.error("MyScript iink SDK not installed")
                return {}

            # Create ink model
            model = InkModel()

            # Add strokes to model
            for stroke in strokes:
                ink_stroke = InkStroke()

                # Add points to stroke
                for i, point in enumerate(stroke["points"]):
                    # Set event type based on point position in stroke
                    if i == 0:
                        event_type = PointerEventType.DOWN
                    elif i == len(stroke["points"]) - 1:
                        event_type = PointerEventType.UP
                    else:
                        event_type = PointerEventType.MOVE

                    # Add point
                    ink_point = Point()
                    ink_point.x = point["x"]
                    ink_point.y = point["y"]
                    ink_point.pressure = (
                        point["pressure"] if "pressure" in point else 1.0
                    )
                    ink_point.timestamp = (
                        point["timestamp"] if "timestamp" in point else 0
                    )
                    ink_point.eventType = event_type

                    ink_stroke.addPoint(ink_point)

                # Add stroke to model
                model.addStroke(ink_stroke)

            # Convert model to JSON for easier manipulation
            return json.loads(model.toJson())

        except Exception as e:
            logger.error(f"Failed to convert to iink format: {e}")
            return {}

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
            # Check if SDK is initialized
            if not self.initialized:
                logger.error("MyScript iink SDK not initialized")
                return {"error": "SDK not initialized"}

           # Import SDK
           try:
                from iink.iink import (
                    Configuration,
                    ContentBlock,
                    ContentPackage,
                    ContentPart,
                    InkModel,
                    MimeType,
                )
            except ImportError:
                logger.error("MyScript iink SDK not installed")
                return {"error": "SDK not installed"}

            # Create ink model from JSON
            model = InkModel.fromJson(json.dumps(iink_data))

            # Create content package
            package = ContentPackage()

            # Set configuration
            config = Configuration()
            config.setStringProperty("lang", language)

            # Create content part
            part = package.createContentPart(content_type, config)

            # Import ink model
            part.getContent().importInkModel(model)

            # Perform recognition
            part.getContent().processInk()

            # Export results as JIIX (JSON Interactive Ink Exchange)
            jiix = part.getContent().export_(MimeType.JIIX)

            # Parse JIIX
            recognition_result = json.loads(jiix)

            # Close package
            package.close()

            return recognition_result

        except Exception as e:
            logger.error(f"Failed to recognize handwriting: {e}")
            return {"error": str(e)}

    @staticmethod
    def export_content(content_id: str, format_type: str = "text") -> Dict[str, Any]:
        """
        Export recognized content in the specified format.

        Args:
            content_id: Content ID from recognition result
            format_type: Format type (text, JIIX, etc.)

        Returns:
            Exported content
        """
        try:
            # This is a simplified version assuming content_id is already a JIIX result
            # In a real implementation, we would use MyScript SDK to export the content

            # For now, just return the content_id as is
            return {"content": content_id, "format": format_type}

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

            # Convert to iink format
            iink_data = self.convert_to_iink_format(strokes)

            if not iink_data:
                logger.error("Failed to convert to iink format")
                return {"error": "Failed to convert to iink format"}

            # Recognize handwriting
            result = self.recognize_handwriting(iink_data, content_type, language)

            return result

        except Exception as e:
            logger.error(f"Failed to process .rm file: {e}")
            return {"error": str(e)}
