"""Google Docs integration service."""

import os
import logging
from typing import Dict, Any, Optional

from bs4 import BeautifulSoup

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None

from inklink.utils import (
    retry_operation,
    format_error,
    extract_structured_content,
    validate_and_fix_content,
)

logger = logging.getLogger(__name__)


class GoogleDocsService:
    """Service to fetch and convert Google Docs documents."""

    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    def __init__(
        self, credentials_path: Optional[str] = None, token_path: Optional[str] = None
    ):
        """
        Initialize Google Docs service.

        Args:
            credentials_path: Path to OAuth2 client secrets JSON.
            token_path: Path to store user credentials.
        """
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH")
        self.token_path = token_path or os.getenv("GOOGLE_TOKEN_PATH", "token.json")
        self.creds: Optional[Credentials] = None
        self.drive_service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Google and build Drive service."""
        # If Google API client libraries are unavailable, skip authentication
        if not all([Request, Credentials, InstalledAppFlow, build]):
            logger.warning(
                "Google API client libraries not installed; authentication disabled."
            )
            return
        try:
            if os.path.exists(self.token_path):
                self.creds = Credentials.from_authorized_user_file(
                    self.token_path, self.SCOPES
                )
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                # Save credentials
                with open(self.token_path, "w", encoding="utf-8") as token_file:
                    token_file.write(self.creds.to_json())
            self.drive_service = build("drive", "v3", credentials=self.creds)
        except Exception as e:
            logger.error(format_error("auth", "Google Docs authentication failed", e))
            raise

    def fetch(self, url_or_id: str) -> Dict[str, Any]:
        """
        Fetch a Google Docs document by URL or ID.

        Exports the document as HTML and processes it into a structured format
        suitable for document generation.

        Args:
            url_or_id: Google Docs URL or document ID

        Returns:
            Dict with keys: title, structured_content, images
        """
        doc_id = self._extract_doc_id(url_or_id)
        try:
            # Define HTML export function for retry operation
            def export_html():
                if not self.drive_service:
                    raise ValueError("Google Drive service not initialized")
                return (
                    self.drive_service.files()
                    .export(fileId=doc_id, mimeType="text/html")
                    .execute()
                )

            # Fetch HTML with retry handling
            html_content = retry_operation(
                export_html, operation_name="Google Docs export"
            )

            # Process HTML into structured content
            content = extract_structured_content(html_content, url_or_id)

            # Validate and ensure content structure is complete
            return validate_and_fix_content(content, url_or_id)

        except Exception as e:
            error_msg = format_error(
                "googledocs", "Failed to fetch Google Docs document", e
            )
            logger.error(error_msg)
            return {
                "title": url_or_id,
                "structured_content": [
                    {
                        "type": "paragraph",
                        "content": f"Could not fetch Google Docs doc {url_or_id}: {e}",
                    }
                ],
                "images": [],
            }

    def _extract_doc_id(self, url_or_id: str) -> str:
        """
        Extract document ID from Google Docs URL, or return as-is.

        Args:
            url_or_id: Google Docs URL or document ID

        Returns:
            Extracted document ID
        """
        from urllib.parse import urlparse

        try:
            parsed_url = urlparse(url_or_id)
            # Only extract ID for official Google Docs URLs at the expected path
            if parsed_url.hostname == "docs.google.com":
                # Expect path like '/document/d/<ID>/...'
                path = parsed_url.path or ""
                # Split into segments ['', 'document', 'd', '<ID>', ...]
                segments = path.split("/")
                if (
                    len(segments) >= 4
                    and segments[1] == "document"
                    and segments[2] == "d"
                    and segments[3]
                ):
                    return segments[3]
        except Exception:
            # If parsing fails or unexpected format, return input as-is
            pass
        return url_or_id
