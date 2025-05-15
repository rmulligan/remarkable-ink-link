"""Authentication UI for reMarkable Cloud pairing."""

import os
import re
import subprocess

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from inklink.config import CONFIG

app = FastAPI()


@app.get("/auth", response_class=HTMLResponse)
def auth_form():
    # Display instructions for pairing code authentication
    return HTMLResponse(
        """
        <html>
          <head><title>InkLink reMarkable Pairing</title></head>
          <body>
            <h1>Pair InkLink with your reMarkable</h1>
            <p>To authenticate InkLink with your reMarkable Cloud account, get your one-time pairing code.</p>
            <p><strong>Note:</strong> rmapi currently only accepts the 8-digit pairing codes from device pairing.</p>
            <ol>
              <li>Navigate to <a href="https://my.remarkable.com/device/remarkable?showOtp=true" target="_blank">https://my.remarkable.com/device/remarkable?showOtp=true</a></li>
              <li>Copy the 8-digit code shown on the remarkable device pairing page.</li>
              <li>Paste it below and click Connect.</li>
            </ol>
            <form action="/auth" method="post">
              <label>Pairing Code: <input type="text" name="code" required></label><br/>
              <button type="submit">Connect</button>
            </form>
          </body>
        </html>
        """,
        status_code=200,
    )


@app.post("/auth", response_class=HTMLResponse)
def auth_submit(code: str = Form(...)):
    # Validate the pairing code - only allow alphanumeric characters and hyphens
    if not re.match(r"^[a-zA-Z0-9\-]+$", code):
        return HTMLResponse(
            "<html><body><h2>Invalid pairing code format</h2></body></html>",
            status_code=400,
        )

    # Run ddvk rmapi pairing using the provided pairing code
    # Path to rmapi executable
    rmapi_path = CONFIG.get("RMAPI_PATH", "rmapi")

    # Validate and resolve the rmapi path to prevent path traversal
    if os.path.isabs(rmapi_path):
        # If absolute path, validate it exists
        rmapi = os.path.realpath(rmapi_path)  # Resolve symlinks
    else:
        # If relative path, look in PATH or use which to find it
        import shutil

        rmapi = shutil.which(rmapi_path)
        if not rmapi:
            return HTMLResponse(
                "<html><body><h2>Configuration error: rmapi not found</h2></body></html>",
                status_code=500,
            )
        rmapi = os.path.realpath(rmapi)  # Resolve symlinks

    # Define allowed directories for rmapi executable
    allowed_dirs = [
        "/usr/bin",
        "/usr/local/bin",
        "/opt",
        os.path.expanduser("~/.local/bin"),
        os.path.expanduser("~/bin"),
    ]

    # Check if the rmapi path is in an allowed directory
    if not any(rmapi.startswith(allowed_dir) for allowed_dir in allowed_dirs):
        return HTMLResponse(
            "<html><body><h2>Security error: rmapi path not allowed</h2></body></html>",
            status_code=403,
        )

    # Ensure the resolved path exists and is executable
    if not os.path.exists(rmapi) or not os.access(rmapi, os.X_OK):
        return HTMLResponse(
            "<html><body><h2>Configuration error: rmapi not executable</h2></body></html>",
            status_code=500,
        )

    # Use the validated absolute path
    cmd = [rmapi, "config", "--pairing-code", code]

    try:
        # Use subprocess.run with specific arguments to prevent shell injection
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,  # Explicitly disable shell
            timeout=30,  # Add timeout to prevent hanging
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
            # Don't expose stderr/stdout in the response to prevent information leakage
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
        # Don't expose exception details to prevent information disclosure
        return HTMLResponse(
            "<html><body><h2>An error occurred</h2><p>Please try again later.</p></body></html>",
            status_code=500,
        )
