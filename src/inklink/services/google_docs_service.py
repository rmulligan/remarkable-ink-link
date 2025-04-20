"""Google Docs integration service."""

import os
import logging
from typing import Dict, Any, Tuple, List, Optional

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

from inklink.utils import retry_operation, format_error, parse_html_container

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

        Returns a dict with keys: title, structured_content, images.
        """
        doc_id = self._extract_doc_id(url_or_id)
        try:

            def export_html():
                return (
                    self.drive_service.files()
                    .export(fileId=doc_id, mimeType="text/html")
                    .execute()
                )

            html_content = retry_operation(
                export_html, operation_name="Google Docs export"
            )
            soup = BeautifulSoup(html_content, "html.parser")
            title = (
                soup.title.string.strip()
                if soup.title and soup.title.string
                else url_or_id
            )
            container = soup.body or soup
            structured, images = self._process_container(container, url_or_id)
            return {"title": title, "structured_content": structured, "images": images}
        except Exception as e:
            logger.error(
                format_error("googledocs", "Failed to fetch Google Docs document", e)
            )
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
        """
        from urllib.parse import urlparse

        try:
            parsed_url = urlparse(url_or_id)
            if parsed_url.hostname == "docs.google.com":
                parts = parsed_url.path.split("/d/")
                if len(parts) > 1:
                    doc = parts[1].split("/")
                    if doc:
                        return doc[0]
        except Exception:
            # If parsing fails, assume it's a document ID
            pass
        return url_or_id

    def _process_container(
        self, container: BeautifulSoup, base_url: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        """
        Process a BeautifulSoup container to extract structured tags and images.
        """
        # Delegate to shared parsing utility
        return parse_html_container(container, base_url)
