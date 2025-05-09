"""Authentication controller for InkLink.

This module provides controllers for handling authentication-related requests.
"""

import logging
from typing import Dict, Any, Optional
from urllib.parse import parse_qs

from inklink.controllers.base_controller import BaseController
from inklink.adapters.rmapi_adapter import RMAPIAdapter
from inklink.config import CONFIG

logger = logging.getLogger(__name__)


class AuthController(BaseController):
    """Controller for handling authentication requests."""

    def __init__(self, rmapi_path: Optional[str] = None):
        """
        Initialize the auth controller.

        Args:
            rmapi_path: Path to the rmapi executable
        """
        super().__init__()
        self.rmapi_adapter = RMAPIAdapter(rmapi_path or CONFIG.get("RMAPI_PATH"))

    def handle(self, method: str = "GET", path: str = "") -> None:
        """
        Handle authentication requests.

        Args:
            method: HTTP method
            path: Request path
        """
        if method == "GET":
            self.handle_get()
        elif method == "POST":
            if path == "/auth/remarkable":
                self.handle_remarkable_auth()
            elif path == "/auth/myscript":
                self.handle_myscript_auth()
            else:
                self.handle_post()
        else:
            self.send_error("Method not allowed", status=405)

    def handle_get(self) -> None:
        """Handle GET request for auth form."""
        html = """<html><body>
        <h1>reMarkable Authentication</h1>
        <p>Go to <a href="https://my.remarkable.com/device/browser/connect" target="_blank">my.remarkable.com/device/browser/connect</a> and get your one-time code.</p>
        <form method="post" action="/auth">
          <label>One-time code: <input type="text" name="code"/></label>
          <button type="submit">Authenticate</button>
        </form>
        </body></html>"""
        self.send_html(html)

    def handle_post(self) -> None:
        """Handle POST request for auth form submission."""
        raw_data, _ = self.read_request_data()

        # Parse form data
        form_data = parse_qs(raw_data.decode("utf-8"))
        code = form_data.get("code", [""])[0].strip()

        if not code:
            self.send_html(
                "<html><body><h1>Error: No code provided.</h1><a href='/auth'>Try again</a></body></html>",
                status=400,
            )
            return

        # Authenticate with reMarkable
        success, message = self._authenticate_with_remarkable(code)

        if success:
            self.send_html(
                "<html><body><h1>Authentication Successful!</h1><p>You can now use the /share endpoint.</p></body></html>"
            )
        else:
            self.send_html(
                f"<html><body><h1>Authentication Failed</h1><pre>{message}</pre><a href='/auth'>Try again</a></body></html>",
                status=400,
            )

    def handle_remarkable_auth(self) -> None:
        """Handle reMarkable authentication via API."""
        _, json_data = self.read_request_data()

        if not json_data:
            self.send_error("Invalid JSON", status=400)
            return

        token = json_data.get("token")
        if not token:
            self.send_error("Missing token", status=400)
            return

        # Store token in memory
        self.get_server().tokens["remarkable"] = token
        self.send_json({"status": "ok"})

    def handle_myscript_auth(self) -> None:
        """Handle MyScript authentication via API."""
        _, json_data = self.read_request_data()

        if not json_data:
            self.send_error("Invalid JSON", status=400)
            return

        app_key = json_data.get("application_key")
        hmac_key = json_data.get("hmac_key")

        if not app_key or not hmac_key:
            self.send_error("Missing keys", status=400)
            return

        # Store keys in memory
        self.get_server().tokens["myscript"] = {
            "app_key": app_key,
            "hmac_key": hmac_key,
        }
        self.send_json({"status": "ok"})

    def _authenticate_with_remarkable(self, code: str) -> tuple[bool, str]:
        """
        Authenticate with reMarkable Cloud using the provided code.

        Args:
            code: One-time authentication code

        Returns:
            Tuple containing success status and message
        """
        logger.info("Starting rmapi authentication with one-time code")
        return self.rmapi_adapter.authenticate_with_code(code)
