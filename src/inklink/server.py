#!/usr/bin/env python3
"""
Pi Share Receiver Server

Receives URLs via HTTP POST, processes them, and uploads to Remarkable Pro.
"""

import json
import os
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Optional, Tuple
import time

# Import configuration module
from inklink.config import CONFIG, setup_logging

# Import service implementations
from inklink.services.qr_service import QRCodeService
from inklink.services.pdf_service import PDFService
from inklink.services.web_scraper_service import WebScraperService
from inklink.services.document_service import DocumentService
from inklink.services.remarkable_service import RemarkableService

# Set up logging
logger = setup_logging()


class URLHandler(BaseHTTPRequestHandler):
    """Handler for URL sharing requests."""

    def setup(self):
        """Set up the handler after the parent is initialized."""
        # First initialize the parent
        super().setup()

        # Then initialize services safely
        self._initialize_services()

    def _initialize_services(self):
        """Initialize service instances safely."""
        try:
            self.qr_service = QRCodeService(CONFIG["TEMP_DIR"])
            self.pdf_service = PDFService(CONFIG["TEMP_DIR"], CONFIG["OUTPUT_DIR"])
            # Initialize web scraper (no args)
            self.web_scraper = WebScraperService()
            self.document_service = DocumentService(
                CONFIG["TEMP_DIR"], CONFIG["DRAWJ2D_PATH"]
            )
            self.remarkable_service = RemarkableService(
                CONFIG["RMAPI_PATH"], CONFIG["RM_FOLDER"]
            )
        except Exception as e:
            logger.error(f"Error initializing services: {str(e)}")
            logger.error(traceback.format_exc())

    def _is_safe_url(self, url: str) -> bool:
        """Validate URL starts with http(s) and contains only safe characters."""
        import re

        # Only allow http or https and a limited set of URL-safe chars
        SAFE_URL_REGEX = re.compile(
            r'^(https?://)[A-Za-z0-9\-\._~:/\?#\[\]@!\$&\(\)\*\+,;=%]+$'
        )
        # Use fullmatch to ensure the entire URL string matches allowed pattern
        return bool(SAFE_URL_REGEX.fullmatch(url))

    def do_GET(self):
        """Handle GET requests for authentication UI."""
        # Authentication form or file download
        if self.path == "/auth":
            self._send_auth_form()
        elif self.path.startswith("/download/"):
            # Serve generated document for manual download
            from urllib.parse import unquote
            fname = unquote(self.path[len("/download/"):])
            temp_dir = CONFIG.get("TEMP_DIR")
            file_path = os.path.join(temp_dir, fname)
            if not os.path.isfile(file_path):
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f"attachment; filename=\"{fname}\"")
            self.end_headers()
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        else:
            self._send_error("Invalid endpoint. Use /auth, /download/<file>, or /share")

    def _send_auth_form(self):
        """Serve the authentication HTML form."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        html = """<html><body>
        <h1>reMarkable Authentication</h1>
        <p>Go to <a href="https://my.remarkable.com/device/browser/connect" target="_blank">my.remarkable.com/device/browser/connect</a> and get your one-time code.</p>
        <form method="post" action="/auth">
          <label>One-time code: <input type="text" name="code"/></label>
          <button type="submit">Authenticate</button>
        </form>
        </body></html>"""
        self.wfile.write(html.encode("utf-8"))

    def _handle_auth(self):
        """Process authentication code and run rmapi login."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        from urllib.parse import parse_qs
        params = parse_qs(post_data.decode("utf-8"))
        code = params.get("code", [""])[0].strip()
        if not code:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Error: No code provided.</h1><a href='/auth'>Try again</a></body></html>")
            return
        rmapi = CONFIG["RMAPI_PATH"]
        # Use a pseudo-tty to run rmapi login so it can read the one-time code interactively
        try:
            import pty, os, select, subprocess, time

            # Open a new pty pair
            master_fd, slave_fd = pty.openpty()
            # Launch rmapi ls to trigger login flow and then exit
            proc = subprocess.Popen([rmapi, "ls"], stdin=slave_fd, stdout=slave_fd, stderr=slave_fd, close_fds=True)
            os.close(slave_fd)

            output = b""
            # Read until we see the prompt or timeout (up to 10 seconds)
            start = time.time()
            prompt_seen = False
            while time.time() - start < 10:
                r, _, _ = select.select([master_fd], [], [], 0.1)
                if master_fd in r:
                    try:
                        data = os.read(master_fd, 1024)
                    except OSError:
                        break
                    if not data:
                        break
                    output += data
                    if b"Enter one-time code" in output:
                        prompt_seen = True
                        break
            if not prompt_seen:
                proc.terminate()
                os.close(master_fd)
                self.send_response(500)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Error: rmapi login did not prompt for code.</h1></body></html>")
                return

            # Send the one-time code
            try:
                os.write(master_fd, (code + "\n").encode())
            except OSError:
                # Ignore write errors (pty may be closed)
                pass

            # Collect remaining output until process exits
            while True:
                # Stop reading if process has exited
                if proc.poll() is not None:
                    break
                r, _, _ = select.select([master_fd], [], [], 0.1)
                if master_fd in r:
                    try:
                        data = os.read(master_fd, 1024)
                    except OSError:
                        break
                    if not data:
                        break
                    output += data

            exit_code = proc.wait()
            os.close(master_fd)

            # Decode output for display
            try:
                text_out = output.decode('utf-8', errors='ignore')
            except Exception:
                text_out = str(output)

            if exit_code == 0:
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Authentication Successful!</h1><p>You can now use the /share endpoint.</p></body></html>")
            else:
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                msg = f"<html><body><h1>Authentication Failed</h1><pre>{text_out}</pre><a href='/auth'>Try again</a></body></html>"
                self.wfile.write(msg.encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            err = str(e)
            msg = f"<html><body><h1>Error running rmapi login</h1><pre>{err}</pre></body></html>"
            self.wfile.write(msg.encode("utf-8"))

    def do_POST(self):
        """Handle POST request with URL to process."""
        if self.path == "/auth":
            self._handle_auth()
            return
        elif self.path != "/share":
            self._send_error("Invalid endpoint. Use /share or /auth")
            return

        try:
            # Get content length
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_error("Empty request")
                return

            # Read request body
            post_data = self.rfile.read(content_length)
            url = self._extract_url(post_data)

            if not url:
                self._send_error("No valid URL found")
                return

            logger.info(f"Processing URL: {url}")

            # Generate QR code
            qr_path, qr_filename = self.qr_service.generate_qr(url)
            logger.info(f"Generated QR code: {qr_filename}")

            # Process URL based on type
            if self.pdf_service.is_pdf_url(url):
                self._handle_pdf_url(url, qr_path)
            else:
                self._handle_webpage_url(url, qr_path)

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            logger.error(traceback.format_exc())
            self._send_error(f"Error processing request: {str(e)}")

    def _extract_url(self, post_data):
        """Extract URL from request data (JSON or plain text)."""
        # Try to decode as JSON
        try:
            data = json.loads(post_data.decode("utf-8"))

            if url := data.get("url"):
                # Reject URLs containing any whitespace or control characters
                if any(c.isspace() for c in url):
                    return None
                # Trim and parse
                url = url.strip()
                from urllib.parse import urlparse

                parsed = urlparse(url)
                # Validate scheme, netloc, and allowed characters
                if parsed.scheme in ("http", "https") and parsed.netloc and self._is_safe_url(url):
                    return url

        except json.JSONDecodeError:
            pass

        # Try as plain text: decode and validate the raw URL string
        try:
            raw = post_data.decode("utf-8")
        except UnicodeDecodeError:
            return None

        # Reject if any whitespace or control characters present
        if any(c.isspace() for c in raw):
            return None
        # Trim extraneous whitespace at ends
        raw = raw.strip()

        from urllib.parse import urlparse
        parsed = urlparse(raw)
        # Validate scheme and netloc
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return None

        # If the entire URL is safe, return it
        if self._is_safe_url(raw):
            return raw

        # If there is a '<' suffix, strip it and validate the prefix
        if '<' in raw:
            prefix = raw.split('<', 1)[0]
            parsed_pref = urlparse(prefix)
            if (
                parsed_pref.scheme in ("http", "https")
                and parsed_pref.netloc
                and self._is_safe_url(prefix)
            ):
                return prefix
        # If there is a '^' suffix, strip it and validate the prefix
        if '^' in raw:
            prefix = raw.split('^', 1)[0]
            parsed_pref = urlparse(prefix)
            if (
                parsed_pref.scheme in ("http", "https")
                and parsed_pref.netloc
                and self._is_safe_url(prefix)
            ):
                return prefix

        # If there is a '^' suffix, strip it and validate the prefix
        if raw.endswith('^'):
            prefix = raw[:-1]  # Remove the trailing '^'
            parsed_pref = urlparse(prefix)
            if (
                parsed_pref.scheme in ("http", "https")
                and parsed_pref.netloc
                and self._is_safe_url(prefix)
            ):
                return prefix

        # Not a valid URL
        return None

        return None

    def _handle_pdf_url(self, url, qr_path):
        """Handle PDF URL processing."""
        try:
            # Process PDF
            result = self.pdf_service.process_pdf(url, qr_path)
            if not result:
                self._send_error("Failed to process PDF")
                return

            # Create HCL for the PDF instead of uploading directly
            # Create HCL for the PDF, passing through any raster images if available
            hcl_path = self.document_service.create_pdf_hcl(
                result["pdf_path"], result["title"], qr_path, result.get("images")
            )

            if not hcl_path:
                self._send_error("Failed to create HCL script for PDF")
                return

            # Convert to Remarkable document
            rm_path = self.document_service.create_rmdoc(hcl_path, url)
            if not rm_path:
                self._send_error("Failed to convert PDF to Remarkable format")
                return

            # Upload to Remarkable
            success, message = self.remarkable_service.upload(rm_path, result["title"])

            if success:
                # Provide optional download link for the converted PDF ink document
                from urllib.parse import quote
                import os, json
                fname = os.path.basename(rm_path)
                download_url = f"/download/{quote(fname)}"
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                resp = {
                    "success": True,
                    "message": f"PDF uploaded to Remarkable as native ink: {result['title']}",
                    "download": download_url,
                }
                self.wfile.write(json.dumps(resp).encode("utf-8"))
            else:
                self._send_error(f"Failed to upload PDF: {message}")

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            logger.error(traceback.format_exc())
            self._send_error(f"Error processing PDF: {str(e)}")

    def _handle_webpage_url(self, url, qr_path):
        """Handle webpage URL processing."""
        try:
            # Scrape content
            content = self.web_scraper.scrape(url)

            # Create HCL script
            hcl_path = self.document_service.create_hcl(url, qr_path, content)
            if not hcl_path:
                self._send_error("Failed to create HCL script")
                return

            # Convert to Remarkable document
            rm_path = self.document_service.create_rmdoc(hcl_path, url)
            if not rm_path:
                self._send_error("Failed to convert to Remarkable format")
                return

            # Upload to Remarkable
            success, message = self.remarkable_service.upload(rm_path, content["title"])

            if success:
                # Provide optional download link for the converted document
                from urllib.parse import quote
                import os, json
                fname = os.path.basename(rm_path)
                download_url = f"/download/{quote(fname)}"
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                resp = {
                    "success": True,
                    "message": f"Webpage uploaded to Remarkable: {content['title']}",
                    "download": download_url,
                }
                self.wfile.write(json.dumps(resp).encode("utf-8"))
            else:
                self._send_error(f"Failed to upload document: {message}")

        except Exception as e:
            logger.error(f"Error processing webpage: {str(e)}")
            logger.error(traceback.format_exc())
            self._send_error(f"Error processing webpage: {str(e)}")

    def _send_success(self, message):
        """Send success response."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        response = json.dumps({"success": True, "message": message})

        self.wfile.write(response.encode("utf-8"))

    def _send_error(self, message):
        """Send error response."""
        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = json.dumps({"success": False, "message": message})
        self.wfile.write(response.encode("utf-8"))


def run_server(host: str = None, port: int = None):
    """Start the HTTP server."""
    host = host or CONFIG.get("HOST", "0.0.0.0")
    port = port or CONFIG.get("PORT", 9999)
    server_address = (host, port)
    httpd = HTTPServer(server_address, URLHandler)
    logger = setup_logging()
    logger.info(f"InkLink server listening on {host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server")
        httpd.server_close()
