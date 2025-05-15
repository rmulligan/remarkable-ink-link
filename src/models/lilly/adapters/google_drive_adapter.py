#!/usr/bin/env python3
"""
Google Drive Adapter for Lilly

This adapter provides an interface to access and interact with files stored in Google Drive.
"""

import os
import io
import json
import logging
import datetime
import mimetypes
import tempfile
from typing import List, Dict, Any, Optional, Tuple, Union, BinaryIO
from dataclasses import dataclass
from urllib.parse import quote

# Google API client libraries
try:
    from google.oauth2.credentials import Credentials
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class DriveFile:
    """Google Drive file data structure."""

    id: str
    name: str
    mime_type: str
    parent_id: Optional[str]
    created_time: datetime.datetime
    modified_time: datetime.datetime
    size: Optional[int] = None
    web_view_link: Optional[str] = None
    description: Optional[str] = None
    starred: bool = False
    trashed: bool = False
    shared: bool = False
    owners: List[Dict[str, str]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DriveFile":
        """Create a DriveFile from a dictionary."""
        # Handle date conversion
        created_time = data.get("created_time")
        if isinstance(created_time, str):
            created_time = datetime.datetime.fromisoformat(
                created_time.replace("Z", "+00:00")
            )

        modified_time = data.get("modified_time")
        if isinstance(modified_time, str):
            modified_time = datetime.datetime.fromisoformat(
                modified_time.replace("Z", "+00:00")
            )

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            mime_type=data.get("mime_type", ""),
            parent_id=data.get("parent_id"),
            created_time=created_time,
            modified_time=modified_time,
            size=data.get("size"),
            web_view_link=data.get("web_view_link"),
            description=data.get("description"),
            starred=data.get("starred", False),
            trashed=data.get("trashed", False),
            shared=data.get("shared", False),
            owners=data.get("owners", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "mime_type": self.mime_type,
            "parent_id": self.parent_id,
            "created_time": (
                self.created_time.isoformat() if self.created_time else None
            ),
            "modified_time": (
                self.modified_time.isoformat() if self.modified_time else None
            ),
            "size": self.size,
            "web_view_link": self.web_view_link,
            "description": self.description,
            "starred": self.starred,
            "trashed": self.trashed,
            "shared": self.shared,
            "owners": self.owners,
        }

    def __str__(self) -> str:
        """String representation of file."""
        size_str = f"{int(self.size / 1024)} KB" if self.size else "Unknown size"
        return f"{self.name} ({self.mime_type}, {size_str})"

    @property
    def is_folder(self) -> bool:
        """Check if this is a folder."""
        return self.mime_type == "application/vnd.google-apps.folder"

    @property
    def extension(self) -> str:
        """Get the file extension."""
        if self.is_folder:
            return ""

        # Handle Google Docs formats
        google_formats = {
            "application/vnd.google-apps.document": ".gdoc",
            "application/vnd.google-apps.spreadsheet": ".gsheet",
            "application/vnd.google-apps.presentation": ".gslides",
            "application/vnd.google-apps.drawing": ".gdraw",
            "application/vnd.google-apps.form": ".gform",
            "application/vnd.google-apps.script": ".gs",
        }

        if self.mime_type in google_formats:
            return google_formats[self.mime_type]

        # For regular files, get extension from name
        _, ext = os.path.splitext(self.name)
        return ext


class GoogleDriveAdapter:
    """
    Adapter for interacting with Google Drive.

    This adapter uses the Google Drive API to access and manipulate files and folders.
    """

    # Scope required for full Drive access
    SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(
        self,
        credentials_file: Optional[str] = None,
        token_file: Optional[str] = None,
        service_account_file: Optional[str] = None,
        use_service_account: bool = False,
        cache_dir: Optional[str] = None,
    ):
        """
        Initialize the Google Drive adapter.

        Args:
            credentials_file: Path to client credentials file (default from env var GOOGLE_CLIENT_SECRETS)
            token_file: Path to token file (default from env var GOOGLE_TOKEN_FILE)
            service_account_file: Path to service account credentials file (default from env var GOOGLE_SERVICE_ACCOUNT)
            use_service_account: Whether to use service account authentication
            cache_dir: Directory to cache Drive data
        """
        if not GOOGLE_API_AVAILABLE:
            logger.warning(
                "Google API client libraries not installed. Run: pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2"
            )

        # Get file paths from environment variables if not provided
        self.credentials_file = credentials_file or os.environ.get(
            "GOOGLE_CLIENT_SECRETS"
        )
        self.token_file = token_file or os.environ.get("GOOGLE_TOKEN_FILE")
        self.service_account_file = service_account_file or os.environ.get(
            "GOOGLE_SERVICE_ACCOUNT"
        )
        self.use_service_account = use_service_account

        # Validate required files
        if self.use_service_account and not self.service_account_file:
            logger.warning("Service account file not provided for Google Drive adapter")
        elif not self.use_service_account and (
            not self.credentials_file or not self.token_file
        ):
            logger.warning(
                "Client credentials or token file not provided for Google Drive adapter"
            )

        # Caching settings
        self.cache_dir = cache_dir
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

        # Initialize service as None (lazy initialization)
        self.service = None
        self._folder_cache = {}

        logger.info(
            f"Initialized GoogleDriveAdapter with {'service account' if use_service_account else 'OAuth'} authentication"
        )

    def _get_credentials(self) -> Union[Credentials, None]:
        """
        Get Google API credentials.

        Returns:
            Credentials object or None if authentication failed
        """
        credentials = None

        try:
            if self.use_service_account:
                # Service account authentication
                if not os.path.exists(self.service_account_file):
                    logger.error("Service account file not found")
                    return None

                credentials = ServiceAccountCredentials.from_service_account_file(
                    self.service_account_file, scopes=self.SCOPES
                )
                logger.info("Loaded service account credentials")
            else:
                # OAuth authentication
                if os.path.exists(self.token_file):
                    # Load existing token
                    with open(self.token_file, "r") as token:
                        creds_data = json.load(token)
                        credentials = Credentials.from_authorized_user_info(
                            creds_data, self.SCOPES
                        )

                # Check if token is valid
                if not credentials or not credentials.valid:
                    if (
                        credentials
                        and credentials.expired
                        and credentials.refresh_token
                    ):
                        # Refresh the token
                        credentials.refresh(Request())
                        logger.info("Refreshed Google Drive access token")
                    else:
                        # Get new token
                        if not os.path.exists(self.credentials_file):
                            logger.error("Client secrets file not found")
                            return None

                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_file, self.SCOPES
                        )
                        credentials = flow.run_local_server(port=0)
                        logger.info("Generated new Google Drive access token")

                    # Save the token
                    with open(self.token_file, "w") as token:
                        token.write(credentials.to_json())
                        logger.info("Saved token")

            return credentials

        except Exception as e:
            logger.error(f"Error getting Google Drive credentials: {str(e)}")
            return None

    def _connect(self) -> bool:
        """
        Connect to the Google Drive API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Get credentials
            credentials = self._get_credentials()
            if not credentials:
                logger.error("Failed to get Google Drive credentials")
                return False

            # Build the service
            self.service = build("drive", "v3", credentials=credentials)
            logger.info("Successfully connected to Google Drive API")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Google Drive API: {str(e)}")
            self.service = None
            return False

    def _ensure_connected(self) -> bool:
        """
        Ensure connection to Google Drive API is established.

        Returns:
            True if connected, False otherwise
        """
        if self.service is None:
            return self._connect()

        try:
            # Test connection by listing files
            self.service.files().list(pageSize=1).execute()
            return True
        except Exception:
            logger.info("Google Drive API connection lost. Reconnecting...")
            return self._connect()

    def list_files(
        self,
        folder_id: Optional[str] = "root",
        page_size: int = 100,
        query: Optional[str] = None,
        include_trashed: bool = False,
    ) -> Tuple[bool, Union[List[DriveFile], str]]:
        """
        List files in a folder.

        Args:
            folder_id: ID of the folder to list (default: 'root')
            page_size: Maximum number of files to return
            query: Additional query filter
            include_trashed: Whether to include trashed files

        Returns:
            Tuple of (success, files/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Build the query
            q_parts = []

            if folder_id:
                q_parts.append(f"'{folder_id}' in parents")

            if not include_trashed:
                q_parts.append("trashed = false")

            if query:
                q_parts.append(query)

            q = " and ".join(q_parts)

            # Fields to retrieve
            fields = "nextPageToken, files(id, name, mimeType, parents, createdTime, modifiedTime, size, webViewLink, description, starred, trashed, shared, owners)"

            # List files
            results = (
                self.service.files()
                .list(q=q, pageSize=page_size, fields=fields)
                .execute()
            )

            items = results.get("files", [])
            drive_files = []

            for item in items:
                # Convert to DriveFile
                parent_id = item.get("parents", [None])[0]

                drive_file = DriveFile(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    mime_type=item.get("mimeType", ""),
                    parent_id=parent_id,
                    created_time=datetime.datetime.fromisoformat(
                        item.get("createdTime", "").replace("Z", "+00:00")
                    ),
                    modified_time=datetime.datetime.fromisoformat(
                        item.get("modifiedTime", "").replace("Z", "+00:00")
                    ),
                    size=int(item.get("size", 0)) if "size" in item else None,
                    web_view_link=item.get("webViewLink"),
                    description=item.get("description"),
                    starred=item.get("starred", False),
                    trashed=item.get("trashed", False),
                    shared=item.get("shared", False),
                    owners=item.get("owners", []),
                )

                drive_files.append(drive_file)

            return True, drive_files
        except Exception as e:
            logger.error(f"Error listing files in folder {folder_id}: {str(e)}")
            return False, f"Error listing files: {str(e)}"

    def get_file_by_id(self, file_id: str) -> Tuple[bool, Union[DriveFile, str]]:
        """
        Get a file by its ID.

        Args:
            file_id: File ID

        Returns:
            Tuple of (success, file/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Get file metadata
            file = (
                self.service.files()
                .get(
                    fileId=file_id,
                    fields="id, name, mimeType, parents, createdTime, modifiedTime, size, webViewLink, description, starred, trashed, shared, owners",
                )
                .execute()
            )

            # Convert to DriveFile
            parent_id = file.get("parents", [None])[0]

            drive_file = DriveFile(
                id=file.get("id", ""),
                name=file.get("name", ""),
                mime_type=file.get("mimeType", ""),
                parent_id=parent_id,
                created_time=datetime.datetime.fromisoformat(
                    file.get("createdTime", "").replace("Z", "+00:00")
                ),
                modified_time=datetime.datetime.fromisoformat(
                    file.get("modifiedTime", "").replace("Z", "+00:00")
                ),
                size=int(file.get("size", 0)) if "size" in file else None,
                web_view_link=file.get("webViewLink"),
                description=file.get("description"),
                starred=file.get("starred", False),
                trashed=file.get("trashed", False),
                shared=file.get("shared", False),
                owners=file.get("owners", []),
            )

            return True, drive_file
        except Exception as e:
            logger.error(f"Error getting file {file_id}: {str(e)}")
            return False, f"Error getting file: {str(e)}"

    def search_files(
        self, query: str, page_size: int = 50
    ) -> Tuple[bool, Union[List[DriveFile], str]]:
        """
        Search for files by name or content.

        Args:
            query: Search query
            page_size: Maximum number of files to return

        Returns:
            Tuple of (success, files/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Build query to search by name or full text
            q = f"name contains '{query}' or fullText contains '{query}' and trashed = false"

            # List files matching query
            fields = "nextPageToken, files(id, name, mimeType, parents, createdTime, modifiedTime, size, webViewLink, description, starred, trashed, shared, owners)"

            results = (
                self.service.files()
                .list(q=q, pageSize=page_size, fields=fields)
                .execute()
            )

            items = results.get("files", [])
            drive_files = []

            for item in items:
                # Convert to DriveFile
                parent_id = item.get("parents", [None])[0]

                drive_file = DriveFile(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    mime_type=item.get("mimeType", ""),
                    parent_id=parent_id,
                    created_time=datetime.datetime.fromisoformat(
                        item.get("createdTime", "").replace("Z", "+00:00")
                    ),
                    modified_time=datetime.datetime.fromisoformat(
                        item.get("modifiedTime", "").replace("Z", "+00:00")
                    ),
                    size=int(item.get("size", 0)) if "size" in item else None,
                    web_view_link=item.get("webViewLink"),
                    description=item.get("description"),
                    starred=item.get("starred", False),
                    trashed=item.get("trashed", False),
                    shared=item.get("shared", False),
                    owners=item.get("owners", []),
                )

                drive_files.append(drive_file)

            return True, drive_files
        except Exception as e:
            logger.error(f"Error searching files for '{query}': {str(e)}")
            return False, f"Error searching files: {str(e)}"

    def download_file(
        self, file_id: str, destination_path: Optional[str] = None
    ) -> Tuple[bool, Union[str, BinaryIO]]:
        """
        Download a file.

        Args:
            file_id: File ID
            destination_path: Path to save the file (if None, returns file-like object)

        Returns:
            Tuple of (success, path_or_file/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Get file metadata
            status, file = self.get_file_by_id(file_id)
            if not status:
                return False, file

            # Check if it's a Google Docs format
            google_formats = {
                "application/vnd.google-apps.document": (
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ".docx",
                ),
                "application/vnd.google-apps.spreadsheet": (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ".xlsx",
                ),
                "application/vnd.google-apps.presentation": (
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    ".pptx",
                ),
                "application/vnd.google-apps.drawing": ("application/pdf", ".pdf"),
                "application/vnd.google-apps.script": (
                    "application/vnd.google-apps.script+json",
                    ".json",
                ),
            }

            # For Google Docs formats, export in a usable format
            if file.mime_type in google_formats:
                mime_type, extension = google_formats[file.mime_type]

                # Create file path if not provided
                if destination_path is None:
                    temp_dir = tempfile.gettempdir()
                    destination_path = os.path.join(temp_dir, f"{file.name}{extension}")

                # Export the file
                request = self.service.files().export_media(
                    fileId=file_id, mimeType=mime_type
                )
            else:
                # For regular files, download directly
                if destination_path is None:
                    temp_dir = tempfile.gettempdir()
                    destination_path = os.path.join(temp_dir, file.name)

                # Download the file
                request = self.service.files().get_media(fileId=file_id)

            # Download to file or memory
            if destination_path:
                with open(destination_path, "wb") as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()

                logger.info(f"Downloaded file {file.name} to {destination_path}")
                return True, destination_path
            else:
                # Return file-like object
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

                fh.seek(0)
                logger.info(f"Downloaded file {file.name} to memory")
                return True, fh

        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {str(e)}")
            return False, f"Error downloading file: {str(e)}"

    def create_folder(
        self, name: str, parent_id: Optional[str] = None
    ) -> Tuple[bool, Union[DriveFile, str]]:
        """
        Create a new folder.

        Args:
            name: Folder name
            parent_id: Parent folder ID (default: root)

        Returns:
            Tuple of (success, folder/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Set file metadata
            file_metadata = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            }

            # Set parent if provided
            if parent_id:
                file_metadata["parents"] = [parent_id]

            # Create the folder
            file = (
                self.service.files()
                .create(
                    body=file_metadata,
                    fields="id, name, mimeType, parents, createdTime, modifiedTime, webViewLink",
                )
                .execute()
            )

            # Convert to DriveFile
            parent_id = file.get("parents", [None])[0]

            folder = DriveFile(
                id=file.get("id", ""),
                name=file.get("name", ""),
                mime_type=file.get("mimeType", ""),
                parent_id=parent_id,
                created_time=datetime.datetime.fromisoformat(
                    file.get("createdTime", "").replace("Z", "+00:00")
                ),
                modified_time=datetime.datetime.fromisoformat(
                    file.get("modifiedTime", "").replace("Z", "+00:00")
                ),
                size=None,
                web_view_link=file.get("webViewLink"),
            )

            logger.info(f"Created folder {name} with ID {folder.id}")

            # Update folder cache
            self._folder_cache[name] = folder.id

            return True, folder
        except Exception as e:
            logger.error(f"Error creating folder {name}: {str(e)}")
            return False, f"Error creating folder: {str(e)}"

    def upload_file(
        self,
        file_path: str,
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[bool, Union[DriveFile, str]]:
        """
        Upload a file.

        Args:
            file_path: Path to the file to upload
            parent_id: Parent folder ID (default: root)
            description: File description

        Returns:
            Tuple of (success, file/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"

            # Get file details
            file_name = os.path.basename(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)

            if mime_type is None:
                mime_type = "application/octet-stream"

            # Set file metadata
            file_metadata = {"name": file_name}

            # Set parent if provided
            if parent_id:
                file_metadata["parents"] = [parent_id]

            # Set description if provided
            if description:
                file_metadata["description"] = description

            # Create media
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

            # Upload the file
            file = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id, name, mimeType, parents, createdTime, modifiedTime, size, webViewLink, description",
                )
                .execute()
            )

            # Convert to DriveFile
            parent_id = file.get("parents", [None])[0]

            drive_file = DriveFile(
                id=file.get("id", ""),
                name=file.get("name", ""),
                mime_type=file.get("mimeType", ""),
                parent_id=parent_id,
                created_time=datetime.datetime.fromisoformat(
                    file.get("createdTime", "").replace("Z", "+00:00")
                ),
                modified_time=datetime.datetime.fromisoformat(
                    file.get("modifiedTime", "").replace("Z", "+00:00")
                ),
                size=int(file.get("size", 0)) if "size" in file else None,
                web_view_link=file.get("webViewLink"),
                description=file.get("description"),
            )

            logger.info(f"Uploaded file {file_name} with ID {drive_file.id}")
            return True, drive_file
        except Exception as e:
            logger.error(f"Error uploading file {file_path}: {str(e)}")
            return False, f"Error uploading file: {str(e)}"

    def update_file(
        self, file_id: str, file_path: str
    ) -> Tuple[bool, Union[DriveFile, str]]:
        """
        Update a file's contents.

        Args:
            file_id: ID of the file to update
            file_path: Path to the new file contents

        Returns:
            Tuple of (success, file/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"

            # Get mime type
            mime_type, _ = mimetypes.guess_type(file_path)

            if mime_type is None:
                mime_type = "application/octet-stream"

            # Create media
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

            # Update the file
            file = (
                self.service.files()
                .update(
                    fileId=file_id,
                    media_body=media,
                    fields="id, name, mimeType, parents, createdTime, modifiedTime, size, webViewLink, description",
                )
                .execute()
            )

            # Convert to DriveFile
            parent_id = file.get("parents", [None])[0]

            drive_file = DriveFile(
                id=file.get("id", ""),
                name=file.get("name", ""),
                mime_type=file.get("mimeType", ""),
                parent_id=parent_id,
                created_time=datetime.datetime.fromisoformat(
                    file.get("createdTime", "").replace("Z", "+00:00")
                ),
                modified_time=datetime.datetime.fromisoformat(
                    file.get("modifiedTime", "").replace("Z", "+00:00")
                ),
                size=int(file.get("size", 0)) if "size" in file else None,
                web_view_link=file.get("webViewLink"),
                description=file.get("description"),
            )

            logger.info(f"Updated file {drive_file.name} with ID {drive_file.id}")
            return True, drive_file
        except Exception as e:
            logger.error(f"Error updating file {file_id}: {str(e)}")
            return False, f"Error updating file: {str(e)}"

    def update_file_metadata(
        self,
        file_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        starred: Optional[bool] = None,
    ) -> Tuple[bool, Union[DriveFile, str]]:
        """
        Update a file's metadata.

        Args:
            file_id: ID of the file to update
            name: New file name
            description: New file description
            starred: New starred status

        Returns:
            Tuple of (success, file/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Build metadata update
            file_metadata = {}

            if name is not None:
                file_metadata["name"] = name

            if description is not None:
                file_metadata["description"] = description

            if starred is not None:
                file_metadata["starred"] = starred

            # No metadata to update
            if not file_metadata:
                return False, "No metadata provided for update"

            # Update the file metadata
            file = (
                self.service.files()
                .update(
                    fileId=file_id,
                    body=file_metadata,
                    fields="id, name, mimeType, parents, createdTime, modifiedTime, size, webViewLink, description, starred",
                )
                .execute()
            )

            # Convert to DriveFile
            parent_id = file.get("parents", [None])[0]

            drive_file = DriveFile(
                id=file.get("id", ""),
                name=file.get("name", ""),
                mime_type=file.get("mimeType", ""),
                parent_id=parent_id,
                created_time=datetime.datetime.fromisoformat(
                    file.get("createdTime", "").replace("Z", "+00:00")
                ),
                modified_time=datetime.datetime.fromisoformat(
                    file.get("modifiedTime", "").replace("Z", "+00:00")
                ),
                size=int(file.get("size", 0)) if "size" in file else None,
                web_view_link=file.get("webViewLink"),
                description=file.get("description"),
                starred=file.get("starred", False),
            )

            logger.info(
                f"Updated metadata for {drive_file.name} with ID {drive_file.id}"
            )
            return True, drive_file
        except Exception as e:
            logger.error(f"Error updating metadata for file {file_id}: {str(e)}")
            return False, f"Error updating metadata: {str(e)}"

    def move_file(self, file_id: str, destination_folder_id: str) -> Tuple[bool, str]:
        """
        Move a file to a different folder.

        Args:
            file_id: ID of the file to move
            destination_folder_id: ID of the destination folder

        Returns:
            Tuple of (success, message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Get current parents
            file = self.service.files().get(fileId=file_id, fields="parents").execute()

            previous_parents = ",".join(file.get("parents", []))

            # Move the file
            file = (
                self.service.files()
                .update(
                    fileId=file_id,
                    addParents=destination_folder_id,
                    removeParents=previous_parents,
                    fields="id, parents",
                )
                .execute()
            )

            logger.info(f"Moved file {file_id} to folder {destination_folder_id}")
            return True, f"File {file_id} moved to folder {destination_folder_id}"
        except Exception as e:
            logger.error(f"Error moving file {file_id}: {str(e)}")
            return False, f"Error moving file: {str(e)}"

    def trash_file(self, file_id: str) -> Tuple[bool, str]:
        """
        Move a file to trash.

        Args:
            file_id: ID of the file to trash

        Returns:
            Tuple of (success, message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Trash the file
            self.service.files().update(
                fileId=file_id, body={"trashed": True}
            ).execute()

            logger.info(f"Moved file {file_id} to trash")
            return True, f"File {file_id} moved to trash"
        except Exception as e:
            logger.error(f"Error trashing file {file_id}: {str(e)}")
            return False, f"Error trashing file: {str(e)}"

    def delete_file(self, file_id: str) -> Tuple[bool, str]:
        """
        Permanently delete a file.

        Args:
            file_id: ID of the file to delete

        Returns:
            Tuple of (success, message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Delete the file
            self.service.files().delete(fileId=file_id).execute()

            logger.info(f"Permanently deleted file {file_id}")
            return True, f"File {file_id} permanently deleted"
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            return False, f"Error deleting file: {str(e)}"

    def get_folder_id(
        self, folder_path: str, create_missing: bool = False
    ) -> Tuple[bool, Union[str, DriveFile]]:
        """
        Get the ID of a folder by path, optionally creating missing folders.

        Args:
            folder_path: Path to the folder (e.g., "Documents/Projects")
            create_missing: Whether to create missing folders

        Returns:
            Tuple of (success, folder_id/folder/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Split path into components
            components = folder_path.strip("/").split("/")

            # Start from root
            current_id = "root"

            # Check cache first
            if folder_path in self._folder_cache:
                return True, self._folder_cache[folder_path]

            # Traverse path
            for component in components:
                # Skip empty components
                if not component:
                    continue

                # Search for the folder
                query = f"name = '{component}' and mimeType = 'application/vnd.google-apps.folder' and '{current_id}' in parents and trashed = false"
                results = (
                    self.service.files()
                    .list(q=query, spaces="drive", fields="files(id, name)")
                    .execute()
                )

                items = results.get("files", [])

                if items:
                    # Folder exists
                    current_id = items[0]["id"]
                elif create_missing:
                    # Create the folder
                    status, result = self.create_folder(component, current_id)
                    if not status:
                        return False, result

                    current_id = result.id
                else:
                    # Folder doesn't exist
                    return False, f"Folder not found: {component} in path {folder_path}"

            # Update cache
            self._folder_cache[folder_path] = current_id

            return True, current_id
        except Exception as e:
            logger.error(f"Error getting folder ID for {folder_path}: {str(e)}")
            return False, f"Error getting folder ID: {str(e)}"

    def get_file_path(self, file_id: str) -> Tuple[bool, Union[str, str]]:
        """
        Get the path of a file or folder.

        Args:
            file_id: File or folder ID

        Returns:
            Tuple of (success, path/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Get file info
            file = (
                self.service.files()
                .get(fileId=file_id, fields="name, parents")
                .execute()
            )

            name = file.get("name", "")
            parents = file.get("parents", [])

            # If no parents, it's at the root
            if not parents:
                return True, f"/{name}"

            # Get parent path
            status, parent_path = self.get_file_path(parents[0])
            if not status:
                return False, parent_path

            # Combine paths
            path = f"{parent_path}/{name}"

            return True, path
        except Exception as e:
            logger.error(f"Error getting path for file {file_id}: {str(e)}")
            return False, f"Error getting file path: {str(e)}"

    def share_file(
        self,
        file_id: str,
        email: str,
        role: str = "reader",
        send_notification: bool = True,
        message: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Share a file with another user.

        Args:
            file_id: ID of the file to share
            email: Email address to share with
            role: Role to grant (reader, writer, commenter, fileOrganizer, organizer, owner)
            send_notification: Whether to send notification email
            message: Optional message for notification email

        Returns:
            Tuple of (success, message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Set permission details
            permission = {"type": "user", "role": role, "emailAddress": email}

            # Create the permission
            # result = (  # Unused variable
            self.service.permissions().create(
                fileId=file_id,
                body=permission,
                sendNotificationEmail=send_notification,
                emailMessage=message,
                fields="id",
            ).execute()
            # )

            logger.info(f"Shared file {file_id} with {email} as {role}")
            return True, f"File shared with {email} as {role}"
        except Exception as e:
            logger.error(f"Error sharing file {file_id} with {email}: {str(e)}")
            return False, f"Error sharing file: {str(e)}"

    def get_shareable_link(
        self, file_id: str, role: str = "reader"
    ) -> Tuple[bool, Union[str, str]]:
        """
        Get a shareable link for a file.

        Args:
            file_id: File ID
            role: Role to grant (reader, writer, commenter)

        Returns:
            Tuple of (success, link/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Check current sharing settings
            file = (
                self.service.files().get(fileId=file_id, fields="permissions").execute()
            )

            permissions = file.get("permissions", [])

            # Check if already shared with anyone
            anyone_permission = None
            for permission in permissions:
                if permission.get("type") == "anyone":
                    anyone_permission = permission
                    break

            # Create or update permission if needed
            if not anyone_permission:
                # Set permission details
                permission = {
                    "type": "anyone",
                    "role": role,
                    "allowFileDiscovery": False,
                }

                # Create the permission
                self.service.permissions().create(
                    fileId=file_id, body=permission, fields="id"
                ).execute()
            elif anyone_permission.get("role") != role:
                # Update the permission
                self.service.permissions().update(
                    fileId=file_id,
                    permissionId=anyone_permission.get("id"),
                    body={"role": role},
                    fields="id",
                ).execute()

            # Get the file link
            file = (
                self.service.files().get(fileId=file_id, fields="webViewLink").execute()
            )

            link = file.get("webViewLink", "")

            logger.info(f"Created shareable link for file {file_id}")
            return True, link
        except Exception as e:
            logger.error(f"Error creating shareable link for file {file_id}: {str(e)}")
            return False, f"Error creating shareable link: {str(e)}"

    def extract_entities_from_file(self, file: DriveFile) -> List[Dict[str, Any]]:
        """
        Extract entities from a file.

        Args:
            file: File to extract entities from

        Returns:
            List of entities with name, type, and context
        """
        entities = []

        # Create File entity
        file_entity = {
            "name": file.name,
            "entityType": "File" if not file.is_folder else "Folder",
            "fileId": file.id,
            "mimeType": file.mime_type,
            "url": file.web_view_link,
            "context": f"Google Drive {'folder' if file.is_folder else 'file'}",
        }

        entities.append(file_entity)

        # Extract owners as Person entities
        if file.owners:
            for owner in file.owners:
                owner_name = owner.get("displayName", "")
                owner_email = owner.get("emailAddress", "")

                if owner_name or owner_email:
                    entities.append(
                        {
                            "name": owner_name or owner_email,
                            "entityType": "Person",
                            "email": owner_email,
                            "context": f"Owner of {file.name}",
                        }
                    )

        # TODO: Add extraction of content entities for common file types

        return entities

    def get_recent_files(
        self, limit: int = 10
    ) -> Tuple[bool, Union[List[DriveFile], str]]:
        """
        Get recently modified files.

        Args:
            limit: Maximum number of files to return

        Returns:
            Tuple of (success, files/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to Google Drive API"

        try:
            # Query for recent files
            query = "trashed = false"

            # List files
            fields = "nextPageToken, files(id, name, mimeType, parents, createdTime, modifiedTime, size, webViewLink, description, starred, trashed, shared, owners)"

            results = (
                self.service.files()
                .list(
                    q=query, pageSize=limit, orderBy="modifiedTime desc", fields=fields
                )
                .execute()
            )

            items = results.get("files", [])
            drive_files = []

            for item in items:
                # Convert to DriveFile
                parent_id = item.get("parents", [None])[0]

                drive_file = DriveFile(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    mime_type=item.get("mimeType", ""),
                    parent_id=parent_id,
                    created_time=datetime.datetime.fromisoformat(
                        item.get("createdTime", "").replace("Z", "+00:00")
                    ),
                    modified_time=datetime.datetime.fromisoformat(
                        item.get("modifiedTime", "").replace("Z", "+00:00")
                    ),
                    size=int(item.get("size", 0)) if "size" in item else None,
                    web_view_link=item.get("webViewLink"),
                    description=item.get("description"),
                    starred=item.get("starred", False),
                    trashed=item.get("trashed", False),
                    shared=item.get("shared", False),
                    owners=item.get("owners", []),
                )

                drive_files.append(drive_file)

            return True, drive_files
        except Exception as e:
            logger.error(f"Error getting recent files: {str(e)}")
            return False, f"Error getting recent files: {str(e)}"

    def close(self):
        """Close the Google Drive service."""
        self.service = None
        logger.info("Closed Google Drive service")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Command-line functionality for testing
if __name__ == "__main__":
    import argparse

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Google Drive Adapter CLI")
    parser.add_argument(
        "--action",
        choices=["list", "search", "get", "download", "upload", "mkdir", "recent"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument("--folder", help="Folder ID or path")
    parser.add_argument("--file", help="File ID or path")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--dest", help="Destination path for downloads or uploads")
    parser.add_argument(
        "--service-account",
        action="store_true",
        help="Use service account authentication",
    )
    args = parser.parse_args()

    # Create adapter instance
    adapter = GoogleDriveAdapter(use_service_account=args.service_account)

    try:
        if args.action == "list":
            if args.folder:
                # If folder is a path
                if "/" in args.folder:
                    status, folder_id = adapter.get_folder_id(args.folder)
                    if not status:
                        print(f"Error: {folder_id}")
                        exit(1)
                else:
                    folder_id = args.folder

                status, files = adapter.list_files(folder_id)
            else:
                status, files = adapter.list_files()

            if status:
                print(f"Found {len(files)} files:")
                for file in files:
                    if file.is_folder:
                        print(f"📁 {file.name} (ID: {file.id})")
                    else:
                        size_str = (
                            f"{int(file.size / 1024)} KB"
                            if file.size
                            else "Unknown size"
                        )
                        print(f"📄 {file.name} ({size_str}) (ID: {file.id})")
            else:
                print(f"Error: {files}")

        elif args.action == "search":
            if not args.query:
                print("Error: --query is required for search action")
                exit(1)

            status, files = adapter.search_files(args.query)
            if status:
                print(f"Found {len(files)} files matching '{args.query}':")
                for file in files:
                    if file.is_folder:
                        print(f"📁 {file.name} (ID: {file.id})")
                    else:
                        size_str = (
                            f"{int(file.size / 1024)} KB"
                            if file.size
                            else "Unknown size"
                        )
                        print(f"📄 {file.name} ({size_str}) (ID: {file.id})")
                    print(f"  Link: {file.web_view_link}")
            else:
                print(f"Error: {files}")

        elif args.action == "get":
            if not args.file:
                print("Error: --file is required for get action")
                exit(1)

            status, file = adapter.get_file_by_id(args.file)
            if status:
                print(f"File details:")
                print(f"Name: {file.name}")
                print(f"ID: {file.id}")
                print(f"Type: {'Folder' if file.is_folder else 'File'}")
                print(f"MIME Type: {file.mime_type}")
                if file.size:
                    print(f"Size: {int(file.size / 1024)} KB")
                print(f"Created: {file.created_time}")
                print(f"Modified: {file.modified_time}")
                print(f"Link: {file.web_view_link}")
            else:
                print(f"Error: {file}")

        elif args.action == "download":
            if not args.file:
                print("Error: --file is required for download action")
                exit(1)

            status, result = adapter.download_file(args.file, args.dest)
            if status:
                print(f"Downloaded file to: {result}")
            else:
                print(f"Error: {result}")

        elif args.action == "upload":
            if not args.file:
                print("Error: --file is required for upload action")
                exit(1)

            if args.folder:
                # If folder is a path
                if "/" in args.folder:
                    status, folder_id = adapter.get_folder_id(
                        args.folder, create_missing=True
                    )
                    if not status:
                        print(f"Error: {folder_id}")
                        exit(1)
                else:
                    folder_id = args.folder

                status, file = adapter.upload_file(args.file, folder_id)
            else:
                status, file = adapter.upload_file(args.file)

            if status:
                print(f"Uploaded file: {file.name}")
                print(f"ID: {file.id}")
                print(f"Link: {file.web_view_link}")
            else:
                print(f"Error: {file}")

        elif args.action == "mkdir":
            if not args.folder:
                print("Error: --folder is required for mkdir action")
                exit(1)

            # If folder is a path
            if "/" in args.folder:
                status, result = adapter.get_folder_id(args.folder, create_missing=True)
                if status:
                    print(f"Created folder: {args.folder}")
                    print(f"ID: {result}")
                else:
                    print(f"Error: {result}")
            else:
                # Create folder in root
                status, folder = adapter.create_folder(args.folder)
                if status:
                    print(f"Created folder: {folder.name}")
                    print(f"ID: {folder.id}")
                else:
                    print(f"Error: {folder}")

        elif args.action == "recent":
            status, files = adapter.get_recent_files()
            if status:
                print(f"Recent files:")
                for file in files:
                    if file.is_folder:
                        print(
                            f"📁 {file.name} (Modified: {file.modified_time.strftime('%Y-%m-%d %H:%M')})"
                        )
                    else:
                        size_str = (
                            f"{int(file.size / 1024)} KB"
                            if file.size
                            else "Unknown size"
                        )
                        print(
                            f"📄 {file.name} ({size_str}) (Modified: {file.modified_time.strftime('%Y-%m-%d %H:%M')})"
                        )
                    print(f"  Link: {file.web_view_link}")
            else:
                print(f"Error: {files}")

    finally:
        # Close connection
        adapter.close()
