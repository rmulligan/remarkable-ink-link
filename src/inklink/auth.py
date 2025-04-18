"""Authentication UI for reMarkable Cloud pairing."""
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import subprocess
import os

app = FastAPI()

@app.get("/auth", response_class=HTMLResponse)
def auth_form():
    return HTMLResponse(
        """
        <html>
          <head><title>InkLink reMarkable Authentication</title></head>
          <body>
            <h1>InkLink reMarkable Cloud Authentication</h1>
            <form action="/auth" method="post">
              <label>Email: <input type="email" name="username" required></label><br/>
              <label>Password: <input type="password" name="password" required></label><br/>
              <button type="submit">Connect</button>
            </form>
          </body>
        </html>
        """, status_code=200)

@app.post("/auth", response_class=HTMLResponse)
def auth_submit(username: str = Form(...), password: str = Form(...)):
    # Run ddvk rmapi config
    rmapi = os.getenv('RMAPI_PATH', 'rmapi')
    cmd = [rmapi, 'config', '--username', username, '--password', password]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return HTMLResponse(
                """
                <html><body>
                  <h2>Authentication successful!</h2>
                  <p>You can close this window.</p>
                </body></html>
                """, status_code=200)
        else:
            return HTMLResponse(
                f"<html><body><h2>Authentication failed</h2><pre>{result.stderr}</pre></body></html>",
                status_code=400)
    except Exception as e:
        return HTMLResponse(
            f"<html><body><h2>Error running rmapi:</h2><pre>{e}</pre></body></html>",
            status_code=500)