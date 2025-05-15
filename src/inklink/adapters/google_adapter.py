"""Google API adapter for InkLink.

This module provides an adapter for Google APIs including Google Drive and Google Docs.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple, BinaryIO, Union
import re
from urllib.parse import urlparse

from inklink.adapters.adapter import Adapter

logger = logging.getLogger(__name__)


class GoogleAPIAdapter(Adapter):
    """Adapter for Google APIs such as Drive and Docs."""

    # OAuth scopes for various Google services
    SCOPES = {
        "drive_readonly": ["https://www.googleapis.com/auth/drive.readonly"],
        "drive_full": ["https://www.googleapis.com/auth/drive"],
        "docs_readonly": ["https://www.googleapis.com/auth/documents.readonly"],
        "docs_full": ["https://www.googleapis.com/auth/documents"],
    }

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        readonly: bool = True,
    ):
        """
        Initialize with Google API credentials.

        Args:
            credentials_path: Path to OAuth2 client secrets JSON
            token_path: Path to store user credentials
            readonly: Whether to use read-only scopes (safer)
        """
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH")
        self.token_path = token_path or os.getenv("GOOGLE_TOKEN_PATH", "token.json")
        self.readonly = readonly

        # Will be set by authenticate()
        self.creds = None
        self.drive_service = None
        self.docs_service = None

        # Attempt to authenticate
        self._authenticate()

    def ping(self) -> bool:
        """
        Check if Google API is available.

        Returns:
            True if API is available, False otherwise
        """
        try:
            if not self.drive_service:
                return False

            # Try a simple operation (list files, limit 1)
            result = self.drive_service.files().list(pageSize=1).execute()
            return "files" in result
        except Exception as e:
            logger.error(f"Google API not available: {e}")
            return False

    def _authenticate(self):
        """Authenticate with Google and build services."""
        try:
            # Import Google libraries - only when needed
            try:
                from google.auth.transport.requests import Request
                from google.oauth2.credentials import Credentials
                from google_auth_oauthlib.flow import InstalledAppFlow
                from googleapiclient.discovery import build
            except ImportError:
                logger.warning(
                    "Google API client libraries not installed; authentication disabled."
                )
                return

            # Determine scopes based on readonly flag
            scopes = []
            if self.readonly:
                scopes.extend(self.SCOPES["drive_readonly"])
                scopes.extend(self.SCOPES["docs_readonly"])
            else:
                scopes.extend(self.SCOPES["drive_full"])
                scopes.extend(self.SCOPES["docs_full"])

            # Load credentials if they exist
            if os.path.exists(self.token_path):
                self.creds = Credentials.from_authorized_user_file(
                    self.token_path, scopes
                )

            # Refresh or create new credentials if needed
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                elif self.credentials_path:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, scopes
                    )
                    self.creds = flow.run_local_server(port=0)
                else:
                    logger.error(
                        "No credentials available for Google API authentication"
                    )
                    return

                # Save credentials
                with open(self.token_path, "w", encoding="utf-8") as token_file:
                    token_file.write(self.creds.to_json())

            # Build services
            self.drive_service = build("drive", "v3", credentials=self.creds)
            self.docs_service = build("docs", "v1", credentials=self.creds)

            logger.info("Google API services initialized successfully")

        except Exception as e:
            logger.error(f"Google API authentication failed: {e}")

    def extract_doc_id(self, url_or_id: str) -> str:
        """
        Extract document ID from Google Docs URL, or return as-is.

        Args:
            url_or_id: Google Docs URL or document ID

        Returns:
            Extracted document ID
        """
        try:
            parsed_url = urlparse(url_or_id)

            # Only extract ID for official Google Docs URLs
            if parsed_url.hostname == "docs.google.com":
                # Parse path: '/document/d/<ID>/...'
                path = parsed_url.path or ""

                # Try standard URL pattern
                segments = path.split("/")
                if (
                    len(segments) >= 4
                    and segments[1] == "document"
                    and segments[2] == "d"
                    and segments[3]
                ):
                    return segments[3]

                # Try edit URL pattern: '/document/d/e/<ID>/...'
                if (
                    len(segments) >= 5
                    and segments[1] == "document"
                    and segments[2] == "d"
                    and segments[3] == "e"
                    and segments[4]
                ):
                    return segments[4]

            # Try to find ID in URL query params
            if parsed_url.query:
                query_params = dict(
                    param.split("=") for param in parsed_url.query.split("&")
                )
                if "id" in query_params:
                    return query_params["id"]

            # Regex pattern for Google Doc IDs
            id_pattern = r"[a-zA-Z0-9_-]{25,}"
            if re.match(id_pattern, url_or_id):
                return url_or_id

        except Exception as e:
            logger.error(f"Error extracting Google Docs ID: {e}")

        # If all parsing fails, return input as-is
        return url_or_id

    def export_doc_as_html(self, doc_id: str) -> Tuple[bool, str]:
        """
        Export a Google Doc as HTML.

        Args:
            doc_id: Google Docs document ID

        Returns:
            Tuple of (success, content_or_error)
        """
        try:
            if not self.drive_service:
                return False, "Google Drive service not initialized"

            # Export the document as HTML
            response = (
                self.drive_service.files()
                .export(fileId=doc_id, mimeType="text/html")
                .execute()
            )

            # Check if response is HTML content
            if isinstance(response, (str, bytes)):
                if isinstance(response, bytes):
                    return True, response.decode("utf-8")
                return True, response

            return False, "Unexpected response format from Google API"

        except Exception as e:
            logger.error(f"Error exporting Google Doc as HTML: {e}")
            return False, str(e)

    def export_doc_as_docx(self, doc_id: str, output_path: str) -> bool:
        """
        Export a Google Doc as DOCX.

        Args:
            doc_id: Google Docs document ID
            output_path: Path to save the exported DOCX file

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.drive_service:
                logger.error("Google Drive service not initialized")
                return False

            # Export the document as DOCX
            response = (
                self.drive_service.files()
                .export(
                    fileId=doc_id,
                    mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
                .execute()
            )

            # Save the file
            with open(output_path, "wb") as f:
                if isinstance(response, bytes):
                    f.write(response)
                else:
                    logger.error("Unexpected response format from Google API")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error exporting Google Doc as DOCX: {e}")
            return False

    def export_doc_as_pdf(self, doc_id: str, output_path: str) -> bool:
        """
        Export a Google Doc as PDF.

        Args:
            doc_id: Google Docs document ID
            output_path: Path to save the exported PDF file

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.drive_service:
                logger.error("Google Drive service not initialized")
                return False

            # Export the document as PDF
            response = (
                self.drive_service.files()
                .export(fileId=doc_id, mimeType="application/pdf")
                .execute()
            )

            # Save the file
            with open(output_path, "wb") as f:
                if isinstance(response, bytes):
                    f.write(response)
                else:
                    logger.error("Unexpected response format from Google API")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error exporting Google Doc as PDF: {e}")
            return False

    def get_document_metadata(self, doc_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get document metadata from Google Docs API.

        Args:
            doc_id: Google Docs document ID

        Returns:
            Tuple of (success, metadata_or_error)
        """
        try:
            if not self.drive_service:
                return False, "Google Drive service not initialized"

            # Get file metadata
            file_metadata = (
                self.drive_service.files()
                .get(
                    fileId=doc_id,
                    fields="name,mimeType,createdTime,modifiedTime,owners,size",
                )
                .execute()
            )

            return True, file_metadata

        except Exception as e:
            logger.error(f"Error getting Google Doc metadata: {e}")
            return False, {"error": str(e)}

    def list_documents(
        self,
        query: str = "mimeType='application/vnd.google-apps.document'",
        max_results: int = 10,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        List Google Docs documents.

        Args:
            query: Search query for files (Google Drive API format)
            max_results: Maximum number of results to return

        Returns:
            Tuple of (success, list_of_docs_or_error)
        """
        try:
            if not self.drive_service:
                return False, "Google Drive service not initialized"

            # List files
            results = (
                self.drive_service.files()
                .list(
                    q=query,
                    pageSize=max_results,
                    fields="files(id, name, createdTime, modifiedTime, owners, webViewLink)",
                )
                .execute()
            )

            files = results.get("files", [])
            return True, files

        except Exception as e:
            logger.error(f"Error listing Google Docs: {e}")
            return False, [{"error": str(e)}]
