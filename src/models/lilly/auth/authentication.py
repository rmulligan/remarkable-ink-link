"""
Unified Authentication Flow for Lilly service adapters.

This module provides a consistent authentication flow for all service adapters
used by Lilly, including Proton Mail, Proton Calendar, and Google Drive.
"""

import http.server
import logging
import socketserver
import time
import urllib.parse
import webbrowser
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Tuple

# Import credential manager
from lilly.auth.credential_manager import CredentialManager

logger = logging.getLogger(__name__)

# Define service types
SERVICE_PROTON_MAIL = "proton_mail"
SERVICE_PROTON_CALENDAR = "proton_calendar"
SERVICE_GOOGLE_DRIVE = "google_drive"


class AuthenticationError(Exception):
    """Exception raised for authentication errors."""

    pass


class AuthenticationBase(ABC):
    """Base class for authentication flows."""

    def __init__(self, credential_manager: Optional[CredentialManager] = None):
        """
        Initialize authentication flow.

        Args:
            credential_manager: Credential manager instance
        """
        self.credential_manager = credential_manager or CredentialManager()
        self.service_name = self._get_service_name()

    @abstractmethod
    def _get_service_name(self) -> str:
        """Get the service name for this authentication flow."""
        pass

    @abstractmethod
    def authenticate(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Authenticate with the service.

        Returns:
            Dict: Authentication credentials
        """
        pass

    def get_credentials(self) -> Optional[Dict[str, Any]]:
        """
        Get stored credentials for this service.

        Returns:
            Dict or None: Credentials or None if not found
        """
        return self.credential_manager.get_credentials(self.service_name)

    def save_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Save credentials for this service.

        Args:
            credentials: Authentication credentials to save

        Returns:
            bool: True if successful, False otherwise
        """
        return self.credential_manager.save_credentials(self.service_name, credentials)

    def is_authenticated(self) -> bool:
        """
        Check if credentials exist for this service.

        Returns:
            bool: True if authenticated, False otherwise
        """
        return self.get_credentials() is not None

    def logout(self) -> bool:
        """
        Delete credentials for this service.

        Returns:
            bool: True if successful, False otherwise
        """
        return self.credential_manager.delete_credentials(self.service_name)


class ProtonMailAuthentication(AuthenticationBase):
    """Authentication flow for Proton Mail via Proton Bridge."""

    def _get_service_name(self) -> str:
        return SERVICE_PROTON_MAIL

    def authenticate(
        self,
        username: str,
        password: str,
        bridge_host: str = "127.0.0.1",
        imap_port: int = 1143,
        smtp_port: int = 1025,
    ) -> Dict[str, Any]:
        """
        Authenticate with Proton Mail via Proton Bridge.

        Args:
            username: Proton Mail username/email
            password: Proton Mail password
            bridge_host: Proton Bridge host address
            imap_port: IMAP port for Proton Bridge
            smtp_port: SMTP port for Proton Bridge

        Returns:
            Dict: Authentication credentials

        Raises:
            AuthenticationError: If authentication fails
        """
        # For Proton Bridge, we only store credentials
        # The actual connection test will be done in the adapter
        credentials = {
            "username": username,
            "password": password,
            "bridge_host": bridge_host,
            "imap_port": imap_port,
            "smtp_port": smtp_port,
            "timestamp": int(time.time()),
        }

        if self.save_credentials(credentials):
            return credentials
        else:
            raise AuthenticationError("Failed to save Proton Mail credentials")


class ProtonCalendarAuthentication(AuthenticationBase):
    """Authentication flow for Proton Calendar via Proton Bridge."""

    def _get_service_name(self) -> str:
        return SERVICE_PROTON_CALENDAR

    def authenticate(
        self,
        username: str,
        password: str,
        bridge_host: str = "127.0.0.1",
        caldav_port: int = 8443,
    ) -> Dict[str, Any]:
        """
        Authenticate with Proton Calendar via Proton Bridge.

        Args:
            username: Proton Calendar username/email
            password: Proton Calendar password
            bridge_host: Proton Bridge host address
            caldav_port: CalDAV port for Proton Bridge

        Returns:
            Dict: Authentication credentials

        Raises:
            AuthenticationError: If authentication fails
        """
        # For Proton Bridge, we only store credentials
        # The actual connection test will be done in the adapter
        credentials = {
            "username": username,
            "password": password,
            "bridge_host": bridge_host,
            "caldav_port": caldav_port,
            "timestamp": int(time.time()),
        }

        if self.save_credentials(credentials):
            return credentials
        else:
            raise AuthenticationError("Failed to save Proton Calendar credentials")


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP server handler for OAuth callback."""

    # This will be set by GoogleDriveAuthentication
    oauth_callback: Optional[Callable] = None

    def do_GET(self):
        """Handle GET request with OAuth code."""
        parsed_path = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_path.query)

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        html = """<html><body>
        <h1>Authentication Successful!</h1>
        <p>You can now close this window and return to Lilly.</p>
        </body></html>"""

        self.wfile.write(html.encode())

        # Call the callback function if defined
        if self.oauth_callback and "code" in params:
            self.oauth_callback(params["code"][0])

    def log_message(self, format, *args):
        """Override to silence server logs."""
        pass


class GoogleDriveAuthentication(AuthenticationBase):
    """Authentication flow for Google Drive via OAuth."""

    def _get_service_name(self) -> str:
        return SERVICE_GOOGLE_DRIVE

    def authenticate(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8080/oauth2callback",
        scopes: list = None,
    ) -> Dict[str, Any]:
        """
        Authenticate with Google Drive via OAuth.

        Args:
            client_id: Google API client ID
            client_secret: Google API client secret
            redirect_uri: OAuth redirect URI
            scopes: OAuth scopes to request

        Returns:
            Dict: Authentication credentials including access and refresh tokens

        Raises:
            AuthenticationError: If authentication fails
        """
        # Import here to avoid dependency if not using Google
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import Flow
        except ImportError:
            raise AuthenticationError(
                "Google auth libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2"
            )

        if scopes is None:
            scopes = [
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/drive.metadata.readonly",
            ]

        # Create OAuth flow
        flow = Flow.from_client_config(
            {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uris": [redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=scopes,
            redirect_uri=redirect_uri,
        )

        # Generate authorization URL
        auth_url, _ = flow.authorization_url(
            access_type="offline", include_granted_scopes="true", prompt="consent"
        )

        # Set up local server to handle the callback
        server_address = ("localhost", 8080)

        # Setup callback to get the code
        auth_code = [None]

        def callback_handler(code):
            auth_code[0] = code

        # Set the callback in the handler class
        OAuthCallbackHandler.oauth_callback = callback_handler

        # Start the server
        httpd = socketserver.TCPServer(server_address, OAuthCallbackHandler)

        print(f"Opening browser for Google authentication...")
        webbrowser.open(auth_url)

        # Handle one request, then stop
        httpd.handle_request()
        httpd.server_close()

        if not auth_code[0]:
            raise AuthenticationError("Failed to get authorization code")

        # Exchange code for tokens
        flow.fetch_token(code=auth_code[0])
        credentials = flow.credentials

        # Store credentials
        creds_dict = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
            "timestamp": int(time.time()),
        }

        if self.save_credentials(creds_dict):
            return creds_dict
        else:
            raise AuthenticationError("Failed to save Google Drive credentials")


class AuthenticationProvider:
    """Factory for creating authentication flows."""

    def __init__(self, credential_manager: Optional[CredentialManager] = None):
        """
        Initialize authentication provider.

        Args:
            credential_manager: Credential manager instance
        """
        self.credential_manager = credential_manager or CredentialManager()

    def get_authenticator(self, service_type: str) -> AuthenticationBase:
        """
        Get authenticator for a specific service.

        Args:
            service_type: Type of service

        Returns:
            AuthenticationBase: Authentication flow instance

        Raises:
            ValueError: If service_type is unknown
        """
        if service_type == SERVICE_PROTON_MAIL:
            return ProtonMailAuthentication(self.credential_manager)
        elif service_type == SERVICE_PROTON_CALENDAR:
            return ProtonCalendarAuthentication(self.credential_manager)
        elif service_type == SERVICE_GOOGLE_DRIVE:
            return GoogleDriveAuthentication(self.credential_manager)
        else:
            raise ValueError(f"Unknown service type: {service_type}")

    def list_authenticated_services(self) -> list:
        """
        List all authenticated services.

        Returns:
            list: List of authenticated service names
        """
        return self.credential_manager.list_services()
