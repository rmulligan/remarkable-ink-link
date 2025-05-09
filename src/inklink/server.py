#!/usr/bin/env python3
"""
InkLink Server

Receives URLs via HTTP POST, processes them, and uploads to Remarkable.
"""
import json
import logging
import os
import time
import traceback
import uuid
import cgi
import subprocess
import io
from typing import Dict, Optional, Tuple, Any, List, cast, IO, TypeVar
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from inklink.config import CONFIG, setup_logging
from inklink.utils import is_safe_url
from inklink.services.qr_service import QRCodeService
from inklink.services.pdf_service import PDFService
from inklink.services.web_scraper_service import WebScraperService
from inklink.services.document_service import DocumentService
from inklink.services.remarkable_service import RemarkableService
from inklink.services.ai_service import AIService

# Define a TypeVar for our custom server type
ServerType = TypeVar("ServerType", bound="CustomHTTPServer")


# Set up logging
logger = logging.getLogger("inklink.server")


class URLHandler(BaseHTTPRequestHandler):
    """Handler for URL sharing requests."""

    def __init__(
        self,
        *args,
        qr_service=None,
        pdf_service=None,
        web_scraper=None,
        document_service=None,
        remarkable_service=None,
        ai_service=None,
        **kwargs,
    ):
        self.qr_service = qr_service or QRCodeService(CONFIG["TEMP_DIR"])
        self.pdf_service = pdf_service or PDFService(
            CONFIG["TEMP_DIR"], CONFIG["OUTPUT_DIR"]
        )
        self.web_scraper = web_scraper or WebScraperService()
        self.document_service = document_service or DocumentService(
            CONFIG["TEMP_DIR"], CONFIG["DRAWJ2D_PATH"]
        )
        self.remarkable_service = remarkable_service or RemarkableService(
            CONFIG["RMAPI_PATH"], CONFIG["RM_FOLDER"]
        )
        self.ai_service = ai_service or AIService()
        super().__init__(*args, **kwargs)

    # _is_safe_url removed; use is_safe_url from utils instead

    def do_GET(self):
        """Handle GET requests for auth, download, and response endpoints."""
        # Authentication form
        if self.path == "/auth":
            self._send_auth_form()
        # File download
        elif self.path.startswith("/download/"):
            self._handle_download()
        # Response endpoint
        elif self.path.startswith("/response"):
            self._handle_response()
        else:
            self._send_error("Invalid endpoint. Use /auth, /download/<file>, /response, or /share")

    def _handle_download(self):
        """Handle download requests for generated documents."""
        from urllib.parse import unquote
        import os.path
        import re

        # Get the filename from the path and sanitize it
        fname = unquote(self.path[len("/download/") :])

        # Prevent path traversal by removing directory components and only allowing specific characters
        safe_fname = re.sub(r"[^a-zA-Z0-9._-]", "", os.path.basename(fname))

        if not safe_fname:
            self.send_response(400)
            self.end_headers()
            return

        temp_dir = CONFIG.get("TEMP_DIR")
        file_path = os.path.join(temp_dir, safe_fname)

        # Verify the file exists and is within the temp directory
        real_path = os.path.realpath(file_path)
        if not real_path.startswith(
            os.path.realpath(temp_dir)
        ) or not os.path.isfile(real_path):
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header(
            "Content-Disposition", f'attachment; filename="{safe_fname}"'
        )
        self.end_headers()

        with open(real_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def _handle_response(self):
        """Handle requests for /response endpoint."""
        query = urlparse(self.path).query
        params = parse_qs(query)
        response_id = params.get("response_id", [None])[0]
        if (
            not response_id
            or response_id not in cast(ServerType, self.server).responses
        ):
            self._send_json({"error": "Invalid response_id"}, status=400)
            return
        resp = cast(ServerType, self.server).responses[response_id]
        self._send_json({"markdown": resp["markdown"], "raw": resp["raw"]})

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
            self.wfile.write(
                b"<html><body><h1>Error: No code provided.</h1><a href='/auth'>Try again</a></body></html>"
            )
            return

        rmapi = CONFIG["RMAPI_PATH"]
        logger.info("Starting rmapi authentication with one-time code")

        # First, try to authenticate using the more direct approach with expect script
        try:
            import tempfile

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
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h1>Authentication Successful!</h1><p>You can now use the /share endpoint.</p></body></html>"
                )
                return

            # If expect script failed, fall back to alternative method
            logger.warning(
                f"Expect script failed with code {process.returncode}, output: {process.stdout}"
            )

        except Exception as e:
            logger.warning(f"Expect script approach failed: {str(e)}")
            # Continue to fallback method

        # Fallback: Try using named pipe approach which is more reliable than PTY
        try:
            import tempfile
            from time import time as get_time

            # Create a named pipe (FIFO)
            pipe_path = os.path.join(
                tempfile.gettempdir(), f"rmapi_auth_{int(get_time())}.pipe"
            )
            try:
                os.mkfifo(pipe_path)
            except Exception as e:
                logger.error(f"Failed to create named pipe: {str(e)}")
                raise

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
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h1>Authentication Successful!</h1><p>You can now use the /share endpoint.</p></body></html>"
                )
            else:
                logger.error(f"Authentication failed: {process.stderr}")
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                msg = f"""<html><body>
                    <h1>Authentication Failed</h1>
                    <pre>{process.stderr}</pre>
                    <a href='/auth'>Try again</a>
                    </body></html>"""
                self.wfile.write(msg.encode("utf-8"))

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            self.send_response(500)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            err = str(e)
            msg = f"""<html><body>
                <h1>Error running rmapi login</h1>
                <pre>{err}</pre>
                <p>Please try again or check server logs.</p>
                <a href='/auth'>Try again</a>
                </body></html>"""
            self.wfile.write(msg.encode("utf-8"))

    def do_POST(self):
        """Handle POST requests for multiple endpoints."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b""

        if self.path == "/auth":
            self._handle_auth()
            return
        elif self.path == "/auth/remarkable":
            try:
                data = json.loads(post_data.decode("utf-8"))
                token = data.get("token")
                if not token:
                    self._send_json({"error": "Missing token"}, status=400)
                    return
                # Store token in memory (replace with secure storage in production)
                cast(ServerType, self.server).tokens["remarkable"] = token
                self._send_json({"status": "ok"})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if self.path == "/auth/myscript":
            try:
                data = json.loads(post_data.decode("utf-8"))
                app_key = data.get("application_key")
                hmac_key = data.get("hmac_key")
                if not app_key or not hmac_key:
                    self._send_json({"error": "Missing keys"}, status=400)
                    return
                self.server.tokens["myscript"] = {
                    "app_key": app_key,
                    "hmac_key": hmac_key,
                }
                self._send_json({"status": "ok"})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if self.path == "/ingest":
            """
            Ingest content from browser extension, Siri shortcut, or web UI.
            Accepts JSON with fields:
              - type: "web", "note", "shortcut", etc.
              - title: Title of the content
              - content: Main content (text, HTML, markdown, etc.)
              - metadata: Optional dict (source_url, tags, etc.)
            """
            try:
                data = json.loads(post_data.decode("utf-8"))
                content_type = data.get("type")
                title = data.get("title")
                content = data.get("content")
                # Get metadata
                metadata = data.get("metadata", {})
                if not content_type or not title or not content:
                    self._send_json({"error": "Missing required fields"}, status=400)
                    return

                # Generate a unique ID for tracking
                content_id = str(uuid.uuid4())
                logger.info(
                    f"Ingested content: type={content_type}, title={title}, id={content_id}"
                )

                # Generate QR code if source_url is provided in metadata
                qr_path = ""
                source_url = metadata.get("source_url", "")
                if source_url and is_safe_url(source_url):
                    try:
                        qr_path, qr_filename = self.qr_service.generate_qr(source_url)
                        logger.info(f"Generated QR code for source URL: {qr_filename}")
                    except Exception as e:
                        logger.warning(f"Failed to generate QR code: {str(e)}")

                # Prepare structured content based on content type
                structured_content = []

                # Process content based on type
                if content_type == "web":
                    # For web content, use as-is if already structured
                    if isinstance(content, list):
                        structured_content = content
                    else:
                        # Default to a single paragraph if content is a string
                        structured_content = [{"type": "paragraph", "content": content}]

                elif content_type == "note":
                    # For plain text notes, convert to paragraphs
                    paragraphs = content.split("\n\n")
                    structured_content = [
                        {"type": "paragraph", "content": p.strip()}
                        for p in paragraphs
                        if p.strip()
                    ]

                elif content_type == "shortcut":
                    # For Siri shortcuts, handle markdown conversion if needed
                    if content.startswith("#"):
                        # Simple markdown parsing
                        lines = content.split("\n")
                        current_item = None

                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue

                            if line.startswith("# "):
                                structured_content.append(
                                    {"type": "h1", "content": line[2:]}
                                )
                            elif line.startswith("## "):
                                structured_content.append(
                                    {"type": "h2", "content": line[3:]}
                                )
                            elif line.startswith("### "):
                                structured_content.append(
                                    {"type": "h3", "content": line[4:]}
                                )
                            elif line.startswith("- ") or line.startswith("* "):
                                if current_item and current_item["type"] == "list":
                                    current_item["items"].append(line[2:])
                                else:
                                    current_item = {"type": "list", "items": [line[2:]]}
                                    structured_content.append(current_item)
                            else:
                                structured_content.append(
                                    {"type": "paragraph", "content": line}
                                )
                    else:
                        structured_content = [{"type": "paragraph", "content": content}]
                else:
                    # Default handling for unknown content types
                    structured_content = [{"type": "paragraph", "content": content}]

                # Add any additional metadata as context
                content_package = {
                    "title": title,
                    "structured_content": structured_content,
                    "images": [],
                }

                # Add any AI processing if needed
                try:
                    if metadata.get("process_with_ai", False):
                        context = {k: v for k, v in metadata.items()}
                        ai_response = self.ai_service.process_query(
                            content, context=context
                        )
                        content_package["ai_summary"] = ai_response
                        logger.info(f"Added AI processing for content: {content_id}")
                except Exception as e:
                    logger.warning(f"AI processing failed: {e}")

                # Convert to reMarkable document
                rm_path = self.document_service.create_rmdoc_from_content(
                    url=source_url or f"inklink:/{content_id}",
                    qr_path=qr_path,
                    content=content_package,
                )

                if not rm_path:
                    self._send_json({"error": "Failed to create document"}, status=500)
                    return

                # Upload to reMarkable if specified
                upload_success = False
                upload_message = ""

                if metadata.get("upload_to_remarkable", True):
                    upload_success, upload_message = self.remarkable_service.upload(
                        rm_path, title
                    )

                    if upload_success:
                        logger.info(f"Uploaded to reMarkable: {title}")
                    else:
                        logger.error(
                            f"Failed to upload to reMarkable: {upload_message}"
                        )

                # Store response for later retrieval
                cast(ServerType, self.server).responses[content_id] = {
                    "content_id": content_id,
                    "title": title,
                    "structured_content": structured_content,
                    "uploaded": upload_success,
                    "upload_message": upload_message,
                    "rm_path": rm_path,
                }

                # Return success status with content ID
                self._send_json(
                    {
                        "status": "processed",
                        "content_id": content_id,
                        "title": title,
                        "uploaded": upload_success,
                        "upload_message": (
                            f"Uploaded to reMarkable: {title}"
                            if upload_success
                            else upload_message
                        ),
                    }
                )
            except Exception as e:
                logger.error(f"Error processing content: {str(e)}")
                logger.error(traceback.format_exc())
                self._send_json({"error": str(e)}, status=400)
            return

        if self.path == "/upload":
            # Minimal multipart parser for .rm file
            env = {"REQUEST_METHOD": "POST"}
            # Headers dictionary for potential future use
            # headers = {k: v for k, v in self.headers.items()}
            fs = cgi.FieldStorage(
                fp=self.rfile, headers=self.headers, environ=env, keep_blank_values=True
            )
            fileitem = fs["file"] if "file" in fs else None
            if not fileitem or not fileitem.file:
                self._send_json({"error": "No file uploaded"}, status=400)
                return
            file_id = str(uuid.uuid4())
            upload_dir = "/tmp/inklink_uploads"
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, f"{file_id}.rm")
            with open(file_path, "wb") as f:
                f.write(fileitem.file.read())
            cast(ServerType, self.server).files[file_id] = file_path
            self._send_json({"file_id": file_id})
            return

        if self.path == "/process":
            try:
                data = json.loads(post_data.decode("utf-8"))
                file_id = data.get("file_id")
                if not file_id or file_id not in cast(ServerType, self.server).files:
                    self._send_json({"error": "Invalid file_id"}, status=400)
                    return
                # Simulate processing and AI response
                response_id = str(uuid.uuid4())
                # For demo: just echo file_id as markdown and raw
                md = f"# Processed file {file_id}\n\nAI response here."
                raw = f"RAW_RESPONSE_FOR_{file_id}"
                cast(ServerType, self.server).responses[response_id] = {
                    "markdown": md,
                    "raw": raw,
                }
                self._send_json({"status": "done", "response_id": response_id})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        # Default: legacy /share endpoint
        if self.path == "/share":
            try:
                url = self._extract_url(post_data)
                if not url:
                    self._send_error("No valid URL found")
                    return
                logger.info(f"Processing URL: {url}")
                qr_path, qr_filename = self.qr_service.generate_qr(url)
                logger.info(f"Generated QR code: {qr_filename}")
                if self.pdf_service.is_pdf_url(url):
                    self._handle_pdf_url(url, qr_path)
                else:
                    self._handle_webpage_url(url, qr_path)
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                logger.error(traceback.format_exc())
                self._send_error(f"Error processing request: {str(e)}")
        else:
            self._send_json({"error": "Invalid endpoint"}, status=404)

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

                parsed = urlparse(url)
                # Validate scheme, netloc, and allowed characters
                if (
                    parsed.scheme in ("http", "https")
                    and parsed.netloc
                    and is_safe_url(url)
                ):
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

        parsed = urlparse(raw)
        # Validate scheme and netloc
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return None

        # If the entire URL is safe, return it
        if is_safe_url(raw):
            return raw

        # If there is a '<' suffix, strip it and validate the prefix
        if "<" in raw:
            prefix = raw.split("<", 1)[0]
            parsed_pref = urlparse(prefix)
            if (
                parsed_pref.scheme in ("http", "https")
                and parsed_pref.netloc
                and is_safe_url(prefix)
            ):
                return prefix

        # Not a valid URL
        return None

    def _handle_pdf_url(self, url, qr_path):
        """Handle PDF URL processing."""
        try:
            # Process PDF
            result = self.pdf_service.process_pdf(url, qr_path)
            if not result:
                self._send_error("Failed to process PDF")
                return

            # First try RCU-based conversion method if available
            rm_path = self.document_service.create_pdf_rmdoc(
                result["pdf_path"], result["title"], qr_path
            )

            # If RCU conversion failed, try HCL-based method with image support
            if not rm_path:
                hcl_path = self.document_service.create_pdf_hcl(
                    result["pdf_path"], result["title"], qr_path, result.get("images")
                )

            # If RCU conversion failed, try legacy conversion
            if not rm_path:
                # Create HCL for the PDF
                hcl_path = self.document_service.create_hcl(
                    url, qr_path, {"title": result["title"], "structured_content": []}
                )

                if not hcl_path:
                    self._send_error("Failed to create HCL script for PDF")
                    return

                # Convert to Remarkable document
                rm_path = self.document_service.create_rmdoc_legacy(
                    url, qr_path, {"title": result["title"]}
                )

                if not rm_path:
                    self._send_error("Failed to convert PDF to Remarkable format")
                    return

            # Upload to Remarkable
            success, message = self.remarkable_service.upload(rm_path, result["title"])

            if success:
                # Provide optional download link for the converted PDF ink document
                from urllib.parse import quote
                import os

                # Create response message
                message = f"PDF uploaded to Remarkable as native ink: {result['title']}"

                # Check if client accepts JSON (modern client)
                accept_header = self.headers.get("Accept", "")
                if "application/json" in accept_header:
                    # Return JSON response with download link for new clients
                    fname = os.path.basename(rm_path)
                    download_url = f"/download/{quote(fname)}"
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    resp = {
                        "success": True,
                        "message": message,
                        "download": download_url,
                    }
                    self.wfile.write(json.dumps(resp).encode("utf-8"))
                else:
                    # Return plain text response for backward compatibility
                    self._send_success(message)
            else:
                self._send_error(f"Failed to upload PDF: {message}")

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            logger.error(traceback.format_exc())
            self._send_error(f"Error processing PDF: {str(e)}")

    def _handle_webpage_url(self, url, qr_path):
        """Handle webpage URL processing."""
        # Using the already imported logger from the top of the file
        try:
            logger.debug(
                f"Starting _handle_webpage_url for url={url}, qr_path={qr_path}"
            )

            # Scrape content
            logger.debug("Calling web_scraper.scrape")
            content = self.web_scraper.scrape(url)
            logger.debug("web_scraper.scrape completed")

            # AI processing of main content
            logger.debug("Calling ai_service.process_query on scraped content")
            main_text = ""
            if isinstance(content.get("content"), str):
                main_text = content["content"]
            elif isinstance(content.get("content"), list):
                # Join all text fields if structured as a list of dicts
                main_text = " ".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in content["content"]
                )
            else:
                main_text = str(content)
            try:
                # Extract context: all content fields except the main text
                context = {k: v for k, v in content.items() if k != "content"}
                ai_response = self.ai_service.process_query(main_text, context=context)
                logger.debug(f"AI response: {ai_response}")
                content["ai_summary"] = ai_response
            except Exception as e:
                logger.error(f"AI service failed: {e}")
                content["ai_summary"] = "AI processing failed."

            # Use new RCU-based direct conversion
            logger.debug("Calling document_service.create_rmdoc_from_content")
            rm_path = self.document_service.create_rmdoc_from_content(
                url, qr_path, content
            )
            logger.debug(
                f"document_service.create_rmdoc_from_content returned: {rm_path}"
            )

            if not rm_path:
                logger.error("Failed to convert to Remarkable format")
                self._send_error("Failed to convert to Remarkable format")
                return

            # Upload to Remarkable
            logger.debug("Calling remarkable_service.upload")
            success, message = self.remarkable_service.upload(rm_path, content["title"])
            logger.debug(
                f"remarkable_service.upload returned: success={success}, message={message}"
            )

            if success:
                # Provide optional download link for the converted document
                from urllib.parse import quote
                import os

                # Create response message
                message = f"Webpage uploaded to Remarkable: {content['title']}"

                # Check if client accepts JSON (modern client)
                accept_header = self.headers.get("Accept", "")
                if "application/json" in accept_header:
                    # Return JSON response with download link for new clients
                    fname = os.path.basename(rm_path)
                    download_url = f"/download/{quote(fname)}"
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    resp = {
                        "success": True,
                        "message": message,
                        "download": download_url,
                    }
                    self.wfile.write(json.dumps(resp).encode("utf-8"))
                else:
                    # Return plain text response for backward compatibility
                    self._send_success(message)
                logger.info(f"Webpage uploaded to Remarkable: {content['title']}")
            else:
                logger.error(f"Failed to upload document: {message}")
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

    def _send_json(self, obj, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode("utf-8"))


class CustomHTTPServer(HTTPServer):
    """Custom HTTP Server with additional attributes for tokens, files, and responses."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize attributes needed by URLHandler
        self.tokens = {}  # Store authentication tokens
        self.files = {}  # Store uploaded files
        self.responses = {}  # Store responses


def run_server(host: Optional[str] = None, port: Optional[int] = None):
    """Start the HTTP server with dependency injection support."""
    # Use string type for HOST and int type for PORT with defaults
    host_value = host if host is not None else CONFIG.get("HOST", "0.0.0.0")
    port_value = port if port is not None else int(CONFIG.get("PORT", 9999))
    server_address = (host_value, port_value)

    # Dependency injection: create service instances here
    qr_service = QRCodeService(CONFIG["TEMP_DIR"])
    pdf_service = PDFService(CONFIG["TEMP_DIR"], CONFIG["OUTPUT_DIR"])
    web_scraper = WebScraperService()
    document_service = DocumentService(CONFIG["TEMP_DIR"], CONFIG["DRAWJ2D_PATH"])
    remarkable_service = RemarkableService(CONFIG["RMAPI_PATH"], CONFIG["RM_FOLDER"])

    def handler_factory(*args, **kwargs):
        return URLHandler(
            *args,
            qr_service=qr_service,
            pdf_service=pdf_service,
            web_scraper=web_scraper,
            document_service=document_service,
            remarkable_service=remarkable_service,
            **kwargs,
        )

    httpd = CustomHTTPServer(server_address, handler_factory)
    logger = setup_logging()
    logger.info(f"InkLink server listening on {host_value}:{port_value}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server")
        httpd.server_close()
