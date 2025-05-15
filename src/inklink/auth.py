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
    rmapi = CONFIG.get("RMAPI_PATH", "rmapi")

    # Ensure rmapi path exists to prevent path traversal
    if not os.path.exists(rmapi):
        return HTMLResponse(
            "<html><body><h2>Configuration error</h2></body></html>",
            status_code=500,
        )

    # Use shlex to properly escape the arguments and prevent command injection
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
