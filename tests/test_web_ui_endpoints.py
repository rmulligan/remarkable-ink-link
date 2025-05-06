import io
import json
import tempfile
from http.server import HTTPServer
from src.inklink.server import URLHandler, run_server

import pytest

class DummyServer:
    def __init__(self):
        self.tokens = {}
        self.files = {}
        self.responses = {}

@pytest.fixture
def handler():
    # Minimal handler instance with dummy server
    class DummyRequest:
        def __init__(self):
            self.headers = {}
            self.rfile = io.BytesIO()
            self.wfile = io.BytesIO()
        def send_response(self, code): pass
        def send_header(self, k, v): pass
        def end_headers(self): pass
    req = DummyRequest()
    h = URLHandler(req, server=DummyServer())
    h.server = h.server  # ensure server attribute
    return h

def test_auth_remarkable(handler):
    handler.path = "/auth/remarkable"
    handler.headers = {"Content-Length": "20"}
    handler.rfile = io.BytesIO(b'{"token":"abc123"}')
    handler.wfile = io.BytesIO()
    handler.do_POST()
    assert handler.server.tokens["remarkable"] == "abc123"

def test_auth_myscript(handler):
    handler.path = "/auth/myscript"
    handler.headers = {"Content-Length": "54"}
    handler.rfile = io.BytesIO(b'{"application_key":"app","hmac_key":"hmac"}')
    handler.wfile = io.BytesIO()
    handler.do_POST()
    assert handler.server.tokens["myscript"]["app_key"] == "app"
    assert handler.server.tokens["myscript"]["hmac_key"] == "hmac"

def test_upload_and_process(monkeypatch, handler):
    # Simulate file upload
    handler.path = "/upload"
    handler.headers = {"Content-Length": "0"}
    handler.rfile = io.BytesIO()
    handler.wfile = io.BytesIO()
    # Skipping multipart parsing for brevity; assume file_id is set
    file_id = "testfileid"
    handler.server.files[file_id] = "/tmp/testfile.rm"
    # Process
    handler.path = "/process"
    handler.headers = {"Content-Length": "25"}
    handler.rfile = io.BytesIO(json.dumps({"file_id": file_id}).encode())
    handler.wfile = io.BytesIO()
    handler.do_POST()
    assert any(handler.server.responses)

def test_response(handler):
    rid = "resp1"
    handler.server.responses[rid] = {"markdown": "# md", "raw": "raw"}
    handler.path = f"/response?response_id={rid}"
    handler.wfile = io.BytesIO()
    handler.do_GET()
    handler.wfile.seek(0)
    resp = handler.wfile.read().decode()
    assert "markdown" in resp and "raw" in resp