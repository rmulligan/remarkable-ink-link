"""Tests for syntax highlighting controller."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from inklink.app import app
from inklink.services.syntax_highlight_service import Token
from inklink.services.syntax_tokens import TokenType

client = TestClient(app)


def test_list_themes():
    """Test listing available themes."""
    response = client.get("/syntax/themes")
    assert response.status_code == 200
    data = response.json()
    assert "themes" in data
    assert isinstance(data["themes"], list)

    # Check that built-in themes are present
    theme_names = [t["name"] for t in data["themes"]]
    assert "monokai" in theme_names
    assert "dark" in theme_names
    assert "light" in theme_names


def test_get_builtin_theme():
    """Test getting a built-in theme."""
    response = client.get("/syntax/themes/monokai")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "monokai"
    assert data["isBuiltIn"] is True


def test_get_nonexistent_theme():
    """Test getting a non-existent theme."""
    response = client.get("/syntax/themes/nonexistent")
    assert response.status_code == 404


def test_delete_builtin_theme():
    """Test that built-in themes cannot be deleted."""
    response = client.delete("/syntax/themes/monokai")
    assert response.status_code == 400


@pytest.fixture
def temp_themes_dir():
    """Create a temporary themes directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        themes_dir = Path(tmpdir) / "themes"
        themes_dir.mkdir()
        yield themes_dir


def test_upload_custom_theme(temp_themes_dir):
    """Test uploading a custom theme."""
    with patch("inklink.controllers.syntax_controller.THEMES_DIR", temp_themes_dir):
        theme_data = {
            "background": "#1e1e1e",
            "foreground": "#d4d4d4",
            "keyword": "#569cd6",
            "string": "#ce9178",
            "comment": "#6a9955",
            "number": "#b5cea8",
            "operator": "#d4d4d4",
            "identifier": "#9cdcfe",
            "function_name": "#dcdcaa",
            "class_name": "#4ec9b0",
        }

        files = {"file": ("custom.json", json.dumps(theme_data), "application/json")}
        data = {"name": "custom"}

        response = client.post("/syntax/themes", data=data, files=files)
        assert response.status_code == 200

        # Check that the file was created
        theme_file = temp_themes_dir / "custom.json"
        assert theme_file.exists()


def test_delete_custom_theme(temp_themes_dir):
    """Test deleting a custom theme."""
    with patch("inklink.controllers.syntax_controller.THEMES_DIR", temp_themes_dir):
        # Create a custom theme file
        theme_file = temp_themes_dir / "custom.json"
        theme_file.write_text("{}")

        response = client.delete("/syntax/themes/custom")
        assert response.status_code == 200
        assert not theme_file.exists()


def test_highlight_code():
    """Test code highlighting endpoint."""
    with patch(
        "inklink.services.syntax_scanner.ScannerFactory.create_scanner"
    ) as mock_scanner_factory:
        # Mock scanner
        mock_scanner = MagicMock()
        mock_tokens = [
            Token(
                type=TokenType.KEYWORD, value="def", start=0, end=3, line=0, column=0
            ),
            Token(
                type=TokenType.IDENTIFIER,
                value="hello",
                start=4,
                end=9,
                line=0,
                column=4,
            ),
        ]
        mock_scanner.scan.return_value = mock_tokens
        mock_scanner_factory.return_value = mock_scanner

        with patch(
            "inklink.services.syntax_highlight_service.SyntaxHighlightCompilerV2.compile"
        ) as mock_compile:
            mock_compile.return_value = "mock_hcl_content"

            request_data = {
                "code": "def hello():",
                "language": "python",
                "theme": "monokai",
                "format": "html",
            }

            response = client.post("/syntax/highlight", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert "html" in data


def test_highlight_code_unsupported_language():
    """Test highlighting with unsupported language."""
    request_data = {"code": "some code", "language": "unsupported", "theme": "monokai"}

    response = client.post("/syntax/highlight", json=request_data)
    assert response.status_code == 400


def test_process_file():
    """Test file processing endpoint."""
    response = client.post(
        "/syntax/process_file", json={"file_id": "test", "theme": "monokai"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response_id" in data
    assert "status" in data


def test_get_settings():
    """Test getting settings."""
    response = client.get("/syntax/settings")
    assert response.status_code == 200
    data = response.json()
    assert "uploadFolder" in data
    assert "autoUpload" in data


def test_save_remarkable_auth():
    """Test saving reMarkable authentication."""
    request_data = {"deviceToken": "test_token"}
    response = client.post("/syntax/auth/remarkable", json=request_data)
    assert response.status_code == 200


def test_save_myscript_auth():
    """Test saving MyScript authentication."""
    request_data = {"apiKey": "test_api", "hmacKey": "test_hmac"}
    response = client.post("/syntax/auth/myscript", json=request_data)
    assert response.status_code == 200


def test_save_cloud_settings():
    """Test saving cloud settings."""
    request_data = {"uploadFolder": "/Test", "autoUpload": True}
    response = client.post("/syntax/settings/cloud", json=request_data)
    assert response.status_code == 200
