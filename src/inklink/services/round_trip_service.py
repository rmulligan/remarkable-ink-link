"""Round-trip service for handling Q&A workflow."""

import json
import logging
import os
import tempfile
import time
from typing import Any, Dict, Optional, Tuple

from inklink.config import CONFIG
from inklink.services.document_service import DocumentService
from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)
from inklink.services.remarkable_service import RemarkableService

logger = logging.getLogger(__name__)


class RoundTripService:
    """Service for handling full round-trip from handwriting to AI and back."""

    def __init__(
        self,
        handwriting_service: Optional[HandwritingRecognitionService] = None,
        document_service: Optional[DocumentService] = None,
        remarkable_service: Optional[RemarkableService] = None,
    ):
        """Initialize with required services.

        Args:
            handwriting_service: Service for handwriting recognition
            document_service: Service for document creation
            remarkable_service: Service for reMarkable upload
        """
        # Initialize services if not provided
        self.temp_dir = CONFIG.get("TEMP_DIR")
        os.makedirs(self.temp_dir, exist_ok=True)

        self.handwriting_service = (
            handwriting_service or HandwritingRecognitionService()
        )
        self.document_service = document_service or DocumentService(
            self.temp_dir, CONFIG.get("DRAWJ2D_PATH")
        )
        self.remarkable_service = remarkable_service or RemarkableService(
            CONFIG.get("RMAPI_PATH"), CONFIG.get("RM_FOLDER")
        )

    def process_handwritten_query(
        self, rm_file_path: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Process a handwritten query from an .rm file.

        Args:
            rm_file_path: Path to .rm file with handwritten query

        Returns:
            Tuple of (success, result dictionary)
        """
        try:
            logger.info(f"Processing handwritten query from {rm_file_path}")

            # Extract strokes from .rm file
            strokes = self.handwriting_service.extract_strokes(rm_file_path)
            if not strokes:
                return False, {"error": "No strokes found in file"}

            # Convert to iink format
            iink_data = self.handwriting_service.convert_to_iink_format(strokes)

            # Recognize handwriting
            recognition_result = self.handwriting_service.recognize_handwriting(
                iink_data
            )
            if not recognition_result.get("success", False):
                return False, {
                    "error": f"Recognition failed: {recognition_result.get('error')}"
                }

            # Export as text
            content_id = recognition_result.get("content_id")
            export_result = self.handwriting_service.export_content(content_id, "text")
            if not export_result.get("success", False):
                return False, {"error": f"Export failed: {export_result.get('error')}"}

            # Extract the recognized text
            recognized_text = export_result.get("content", {}).get("text", "").strip()
            if not recognized_text:
                return False, {"error": "No text recognized"}

            # In a real implementation, this is where you would send the text to an AI service
            # and get a response. For testing purposes, we'll generate a simple response.
            response_text = (
                f"Response to: {recognized_text}\n\nThis is a simulated AI response."
            )

            # Create markdown for the response
            timestamp = int(time.time())
            md_filename = f"response_{timestamp}.md"
            md_path = os.path.join(self.temp_dir, md_filename)

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# Response to Query\n\n")
                f.write(f"**Your Question:** {recognized_text}\n\n")
                f.write(f"**Response:**\n\n{response_text}\n")

            # Convert markdown to .rm format
            rm_path = self.document_service.create_rmdoc_from_content(
                url="",
                qr_path="",
                content={
                    "title": "AI Response",
                    "structured_content": [
                        {"type": "h1", "content": "Response to Query"},
                        {
                            "type": "paragraph",
                            "content": f"Your Question: {recognized_text}",
                        },
                        {"type": "paragraph", "content": f"Response: {response_text}"},
                    ],
                },
            )

            if not rm_path:
                return False, {"error": "Failed to create response document"}

            # Upload to reMarkable
            title = f"Response to Query - {timestamp}"
            success, message = self.remarkable_service.upload(rm_path, title)

            if not success:
                return False, {"error": f"Upload failed: {message}"}

            return True, {
                "recognized_text": recognized_text,
                "response_text": response_text,
                "document_path": rm_path,
                "upload_message": message,
            }

        except Exception as e:
            logger.error(f"Error in round-trip processing: {e}")
            return False, {"error": f"Round-trip processing failed: {str(e)}"}
