"""Integration tests for syntax highlighting functionality."""

import pytest
from unittest.mock import MagicMock, patch

from inklink.services.syntax_scanner import ScannerFactory
from inklink.services.syntax_highlight_service import (
    SyntaxHighlightCompilerV2,
    ThemeColors,
)


class TestSyntaxHighlightingIntegration:
    """Test syntax highlighting integration."""

    def test_python_syntax_highlighting(self):
        """Test Python code syntax highlighting."""
        code = """def hello_world():
    print("Hello, World!")
    return 42"""

        scanner = ScannerFactory.create_scanner("python")
        assert scanner is not None

        tokens = scanner.scan(code)
        assert len(tokens) > 0

        # Check that we have the expected token types
        token_types = {token.type.value for token in tokens}
        assert "keyword" in token_types  # def, return
        assert "string" in token_types  # "Hello, World!"
        assert "number" in token_types  # 42

    def test_javascript_syntax_highlighting(self):
        """Test JavaScript code syntax highlighting."""
        code = """function greet(name) {
    console.log(`Hello, ${name}!`);
    return true;
}"""

        scanner = ScannerFactory.create_scanner("javascript")
        assert scanner is not None

        tokens = scanner.scan(code)
        assert len(tokens) > 0

        # Check that we have the expected token types
        token_types = {token.type.value for token in tokens}
        assert "keyword" in token_types  # function, return
        assert "identifier" in token_types  # greet, name, console, log

    def test_theme_loading(self):
        """Test theme loading functionality."""
        compiler = SyntaxHighlightCompilerV2()

        # Test built-in themes
        monokai = compiler._load_theme("monokai")
        assert monokai.background == "#272822"
        assert monokai.keyword == "#f92672"

        dark = compiler._load_theme("dark")
        assert dark.background == "#1e1e1e"
        assert dark.keyword == "#569cd6"

        light = compiler._load_theme("light")
        assert light.background == "#ffffff"
        assert light.keyword == "#0000ff"

    @patch("inklink.services.syntax_highlight_service.Path.exists")
    @patch("builtins.open")
    def test_custom_theme_loading(self, mock_open, mock_exists):
        """Test loading custom theme from file."""
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.read.return_value = """{
            "background": "#custom",
            "foreground": "#custom",
            "keyword": "#custom",
            "string": "#custom",
            "comment": "#custom",
            "number": "#custom",
            "operator": "#custom",
            "identifier": "#custom",
            "function_name": "#custom",
            "class_name": "#custom"
        }"""
        mock_open.return_value = mock_file

        compiler = SyntaxHighlightCompilerV2()
        theme = compiler._load_theme("custom")

        assert theme.background == "#custom"
        assert theme.keyword == "#custom"

    def test_unsupported_language(self):
        """Test handling of unsupported language."""
        scanner = ScannerFactory.create_scanner("unsupported")
        assert scanner is None

    def test_code_compilation(self):
        """Test full code compilation to HCL."""
        from inklink.services.syntax_highlight_service import Token

        # Create mock tokens
        tokens = [
            Token(type="keyword", value="def", line=0, column=0),
            Token(type="identifier", value="test", line=0, column=4),
            Token(type="punctuation", value="(", line=0, column=8),
            Token(type="punctuation", value=")", line=0, column=9),
            Token(type="punctuation", value=":", line=0, column=10),
        ]

        with patch("inklink.services.drawj2d_service.Drawj2dService") as mock_drawj2d:
            mock_drawj2d.return_value._create_document_structure.return_value = (
                "document {\n"
            )
            mock_drawj2d.return_value._create_polygon.return_value = "polygon"
            mock_drawj2d.return_value._add_draw_element.return_value = "  draw {\n  }\n"
            mock_drawj2d.return_value._create_text.return_value = "text"

            compiler = SyntaxHighlightCompilerV2()
            hcl_content = compiler.compile(tokens, "monokai")

            assert hcl_content is not None
            assert "document" in hcl_content
