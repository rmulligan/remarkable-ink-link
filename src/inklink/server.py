#!/usr/bin/env python3
"""
InkLink Server

Receives URLs via HTTP POST, processes them, and uploads to Remarkable.
"""
import logging
import json
import traceback
import os
import time
import uuid
import cgi
import subprocess
from typing import Dict, Optional, Tuple, Any, List, cast, IO, TypeVar
from http.server import HTTPServer, BaseHTTPRequestHandler
import io
from urllib.parse import urlparse, parse_qs

from inklink.config import CONFIG
from inklink.utils import is_safe_url
from inklink.services.qr_service import QRCodeService
from inklink.services.pdf_service import PDFService
from inklink.services.web_scraper_service import WebScraperService
from inklink.services.document_service import DocumentService
from inklink.services.remarkable_service import RemarkableService

# Define a TypeVar for our custom server type
ServerType = TypeVar('ServerType', bound='CustomHTTPServer')


def setup_logging():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    return logging.getLogger("inklink.server")


# Set up logging
logger = setup_logging()


class URLHandler(BaseHTTPRequestHandler):
    """Handler for URL sharing requests."""

    def __init__(
        self,
        *args,
        qr_service=None,
        pdf_service=None,
        web_scraper=None,
        document_service=None,
        remarkable_service=None,
        ai_service=None,
        **kwargs,
    ):
        from inklink.services.ai_service import AIService

        self.qr_service = qr_service or QRCodeService(CONFIG["TEMP_DIR"])
        self.pdf_service = pdf_service or PDFService(
            CONFIG["TEMP_DIR"], CONFIG["OUTPUT_DIR"]
        )
        self.web_scraper = web_scraper or WebScraperService()
        self.document_service = document_service or DocumentService(
            CONFIG["TEMP_DIR"], CONFIG["DRAWJ2D_PATH"]
        )
        self.remarkable_service = remarkable_service or RemarkableService(
            CONFIG["RMAPI_PATH"], CONFIG["RM_FOLDER"]
        )
        self.ai_service = ai_service or AIService()
        super().__init__(*args, **kwargs)

    # _is_safe_url removed; use is_safe_url from utils instead

    def do_POST(self):
        """Handle POST requests for multiple endpoints."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b""

        if self.path == "/auth/remarkable":
            try:
                data = json.loads(post_data.decode("utf-8"))
                token = data.get("token")
                if not token:
                    self._send_json({"error": "Missing token"}, status=400)
                    return
                # Store token in memory (replace with secure storage in production)
                cast(CustomHTTPServer, self.server).tokens["remarkable"] = token
                self._send_json({"status": "ok"})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if self.path == "/auth/myscript":
            try:
                data = json.loads(post_data.decode("utf-8"))
                app_key = data.get("application_key")
                hmac_key = data.get("hmac_key")
                if not app_key or not hmac_key:
                    self._send_json({"error": "Missing keys"}, status=400)
                    return
                cast(CustomHTTPServer, self.server).tokens["myscript"] = {
                    "app_key": app_key,
                    "hmac_key": hmac_key,
                }
                self._send_json({"status": "ok"})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if self.path == "/ingest":
            """
            Ingest content from browser extension, Siri shortcut, or web UI.
            Accepts JSON with fields:
              - type: "web", "note", "shortcut", etc.
              - title: Title of the content
              - content: Main content (text, HTML, markdown, etc.)
              - metadata: Optional dict (source_url, tags, etc.)
            """
            try:
                data = json.loads(post_data.decode("utf-8"))
                content_type = data.get("type")
                title = data.get("title")
                content = data.get("content")
                metadata = data.get("metadata", {})
                if not content_type or not title or not content:
                    self._send_json({"error": "Missing required fields"}, status=400)
                    return

                # Generate a unique ID for tracking
                content_id = str(uuid.uuid4())
                logger.info(
                    f"Ingested content: type={content_type}, title={title}, id={content_id}"
                )

                # Generate QR code if source_url is provided in metadata
                qr_path = ""
                source_url = metadata.get("source_url", "")
                if source_url and is_safe_url(source_url):
                    try:
                        qr_path, qr_filename = self.qr_service.generate_qr(source_url)
                        logger.info(f"Generated QR code for source URL: {qr_filename}")
                    except Exception as e:
                        logger.warning(f"Failed to generate QR code: {str(e)}")

                # Prepare structured content based on content type
                structured_content = []

                # Process content based on type
                if content_type == "web":
                    structured_content = content if isinstance(content, list) else [{"type": "paragraph", "content": content}]
                elif content_type == "note":
                    paragraphs = content.split("\n\n")
                    structured_content = [
                        {"type": "paragraph", "content": p.strip()}
                        for p in paragraphs
                        if p.strip()
                    ]
                elif content_type == "shortcut" and content.startswith("#"):
                    lines = content.split("\n")
                    current_item = None
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("# "):
                            structured_content.append({"type": "h1", "content": line[2:]})
                        elif line.startswith("## "):
                            structured_content.append({"type": "h2", "content": line[3:]})
                        elif line.startswith("### "):
                            structured_content.append({"type": "h3", "content": line[4:]})
                        elif line.startswith(("- ", "* ")):
                            if current_item and current_item["type"] == "list":
                                current_item["items"].append(line[2:])
                            else:
                                current_item = {"type": "list", "items": [line[2:]]}
                                structured_content.append(current_item)
                        else:
                            structured_content.append({"type": "paragraph", "content": line})
                else:
                    structured_content = [{"type": "paragraph", "content": content}]

                # Add any additional metadata as context
                content_package = {
                    "title": title,
                    "structured_content": structured_content,
                    "images": [],
                }

                # Add any AI processing if needed
                try:
                    if metadata.get("process_with_ai", False):
                        context = dict(metadata)
                        # Ensure content is a string for process_query
                        query_text = (
                            "\n".join(content) if isinstance(content, list) else str(content)
                        )
                        ai_response = self.ai_service.process_query(
                            query_text, context=context
                        )
                        content_package["ai_summary"] = ai_response
                        logger.info(f"Added AI processing for content: {content_id}")
                except Exception as e:
                    logger.warning(f"AI processing failed: {e}")

                # Convert to reMarkable document
                rm_path = self.document_service.create_rmdoc_from_content(
                    url=source_url or f"inklink:/{content_id}",
                    qr_path=qr_path,
                    content=content_package,
                )

                if not rm_path:
                    self._send_json({"error": "Failed to create document"}, status=500)
                    return

                # Upload to reMarkable if specified
                upload_success = False
                upload_message = ""

                if metadata.get("upload_to_remarkable", True):
                    upload_success, upload_message = self.remarkable_service.upload(
                        rm_path, title
                    )

                    if upload_success:
                        logger.info(f"Uploaded to reMarkable: {title}")
                    else:
                        logger.error(
                            f"Failed to upload to reMarkable: {upload_message}"
                        )

                # Store response for later retrieval
                cast(CustomHTTPServer, self.server).responses[content_id] = {
                    "content_id": content_id,
                    "title": title,
                    "structured_content": structured_content,
                    "uploaded": upload_success,
                    "upload_message": upload_message,
                    "rm_path": rm_path,
                }

                # Return success status with content ID
                self._send_json(
                    {
                        "status": "processed",
                        "content_id": content_id,
                        "title": title,
                        "uploaded": upload_success,
                        "upload_message": (
                            f"Uploaded to reMarkable: {title}" if upload_success else upload_message
                        ),
                    }
                )
            except Exception as e:
                self._log_and_send_json_error(str(e), status=400)
            return

        if self.path == "/upload":
            # Minimal multipart parser for .rm file
            env = {"REQUEST_METHOD": "POST"}
            # Read the content from self.rfile and wrap it in io.BytesIO for compatibility
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length) if content_length > 0 else b""
            fs = cgi.FieldStorage(
                fp=io.BytesIO(post_body), headers=self.headers, environ=env, keep_blank_values=True
            )
            fileitem = fs["file"] if "file" in fs else None
            if not fileitem or not fileitem.file:
                self._send_json({"error": "No file uploaded"}, status=400)
                return
            file_id = str(uuid.uuid4())
            upload_dir = "/tmp/inklink_uploads"
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, f"{file_id}.rm")
            with open(file_path, "wb") as f:
                f.write(fileitem.file.read())
            cast(CustomHTTPServer, self.server).files[file_id] = file_path
            self._send_json({"file_id": file_id})
            return

        if self.path == "/process":
            try:
                data = json.loads(post_data.decode("utf-8"))
                file_id = data.get("file_id")
                if not file_id or file_id not in cast(CustomHTTPServer, self.server).files:
                    self._send_json({"error": "Invalid file_id"}, status=400)
                    return
                # Simulate processing and AI response
                response_id = str(uuid.uuid4())
                # For demo: just echo file_id as markdown and raw
                md = f"# Processed file {file_id}\n\nAI response here."
                raw = f"RAW_RESPONSE_FOR_{file_id}"
                cast(CustomHTTPServer, self.server).responses[response_id] = {"markdown": md, "raw": raw}
                self._send_json({"status": "done", "response_id": response_id})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        # Default: legacy /share endpoint
        if self.path == "/share":
            try:
                url = self._extract_url(post_data)
                if not url:
                    self._log_and_send_error("No valid URL found")
                    return
                logger.info(f"Processing URL: {url}")
                qr_path, qr_filename = self.qr_service.generate_qr(url)
                logger.info(f"Generated QR code: {qr_filename}")
                if self.pdf_service.is_pdf_url(url):
                    self._handle_pdf_url(url, qr_path)
                else:
                    self._handle_webpage_url(url, qr_path)
            except Exception as e
