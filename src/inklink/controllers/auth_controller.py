"""Authentication controller for InkLink.

This module provides controllers for handling authentication-related requests.
"""

import os
import logging
import subprocess
import tempfile
from typing import Dict, Any
from urllib.parse import parse_qs

from inklink.controllers.base_controller import BaseController
from inklink.config import CONFIG

logger = logging.getLogger(__name__)


class AuthController(BaseController):
    """Controller for handling authentication requests."""

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
        rmapi = CONFIG["RMAPI_PATH"]
        logger.info("Starting rmapi authentication with one-time code")

        # First try expect script approach
        try:
            # Create a temporary expect script file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".exp", delete=False
            ) as expect_file:
                expect_path = expect_file.name
                expect_file.write(
                    f"""#!/usr/bin/expect -f
                set timeout 30
                set code "{code}"

                spawn {rmapi} ls
                expect {{
                    "Enter one-time code:" {{
                        send "$code\\r"
                        exp_continue
                    }}
                    "Permanent token stored" {{
                        exit 0
                    }}
                    eof {{
                        exit 1
                    }}
                    timeout {{
                        exit 2
                    }}
                }}
                """
                )

            # Make the script executable
            os.chmod(expect_path, 0o755)

            # Run the expect script
            process = subprocess.run(
                [expect_path], capture_output=True, text=True, timeout=45
            )

            # Remove the temporary script
            try:
                os.unlink(expect_path)
            except Exception:
                pass

            # Check if authentication was successful
            if process.returncode == 0:
                logger.info("Authentication successful using expect script")
                return True, "Authentication successful"

            # If expect script failed, log the details
            logger.warning(
                f"Expect script failed with code {process.returncode}, output: {process.stdout}"
            )

        except Exception as e:
            logger.warning(f"Expect script approach failed: {str(e)}")

        # Fallback to named pipe approach
        try:
            # Create a named pipe (FIFO)
            pipe_path = os.path.join(
                tempfile.gettempdir(), f"rmapi_auth_{int(time.time())}.pipe"
            )
            try:
                os.mkfifo(pipe_path)
            except Exception as e:
                logger.error(f"Failed to create named pipe: {str(e)}")
                return False, f"Failed to create pipe: {str(e)}"

            # Start a process that will write the code to the pipe
            with open(pipe_path, "w") as fifo:
                # Write the code with a newline
                fifo.write(f"{code}\n")
                fifo.flush()

                # Run rmapi with stdin from the pipe
                process = subprocess.run(
                    [rmapi, "ls"],
                    stdin=open(pipe_path, "r"),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

            # Remove the pipe
            try:
                os.unlink(pipe_path)
            except Exception:
                pass

            # Check the result
            if process.returncode == 0:
                logger.info("Authentication successful using named pipe")
                return True, "Authentication successful"
            else:
                logger.error(f"Authentication failed: {process.stderr}")
                return False, process.stderr

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False, str(e)
