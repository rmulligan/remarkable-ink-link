"""Authentication UI for reMarkable Cloud pairing."""

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import subprocess
import os
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
    # Run ddvk rmapi pairing using the provided pairing code
    # Path to rmapi executable
    rmapi = CONFIG.get("RMAPI_PATH", "rmapi")
    # Use pairing code authentication; adjust flag as per rmapi version
    cmd = [rmapi, "config", "--pairing-code", code]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
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
            err = result.stderr or result.stdout
            return HTMLResponse(
                f"<html><body><h2>Authentication failed</h2><pre>{err}</pre></body></html>",
                status_code=400,
            )
    except Exception as e:
        return HTMLResponse(
            f"<html><body><h2>Error running rmapi:</h2><pre>{e}</pre></body></html>",
            status_code=500,
        )
