import os
import re
import shlex
import subprocess

from fastapi import Form
from fastapi.responses import HTMLResponse

from inklink.config import CONFIG


def get_auth_success_response() -> HTMLResponse:
    """
    Return a simple HTML response indicating successful authentication.

    This response does not contain the result details to avoid information disclosure.
    """
    return HTMLResponse(
        """
        <html>
          <head>
            <title>Authentication</title>
          </head>
          <body>
            <h1>Authentication</h1>
            <form method="post" action="/auth/submit">
              <label for="code">Pairing Code:</label>
              <input type="text" id="code" name="code" required>
              <button type="submit">Submit</button>
            </form>
          </body>
        </html>
        """,
        status_code=200,
    )


def auth_submit(code: str = Form(...)):
    # Validate the pairing code - only allow alphanumeric characters and hyphens
    if not re.match(r"^[a-zA-Z0-9\-]+$", code):
        return HTMLResponse(
            "<html><body><h2>Invalid pairing code format</h2></body></html>",
            status_code=400,
        )

    # Run ddvk rmapi pairing using the provided pairing code
    # Path to rmapi executable
    rmapi = CONFIG.get("RMAPI_PATH", "rmapi")

    # Ensure rmapi path is safe
    if not os.path.exists(rmapi):
        return HTMLResponse(
            "<html><body><h2>Configuration error</h2></body></html>",
            status_code=500,
        )

    # Use shlex to properly escape the arguments
    cmd = [rmapi, "config", "--pairing-code", shlex.quote(code)]

    try:
        # Use subprocess.run with specific arguments to prevent shell injection
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,  # Explicitly disable shell
            timeout=30,  # Add timeout to prevent hanging
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},  # Limit environment
        )

        if result.returncode == 0:
            return HTMLResponse(
                """
                <html><body>
                  <h2>Authentication successful!</h2>
                  <p>You may now close this window and restart the server.</p>
                </body></html>
                """,
                status_code=200,
            )
        else:
            # Don't expose stderr/stdout in the response
            return HTMLResponse(
                "<html><body><h2>Authentication failed</h2><p>Please check your pairing code and try again.</p></body></html>",
                status_code=400,
            )
    except subprocess.TimeoutExpired:
        return HTMLResponse(
            "<html><body><h2>Request timed out</h2><p>Please try again.</p></body></html>",
            status_code=500,
        )
    except Exception:
        # Don't expose exception details
        return HTMLResponse(
            "<html><body><h2>An error occurred</h2><p>Please try again later.</p></body></html>",
            status_code=500,
        )
