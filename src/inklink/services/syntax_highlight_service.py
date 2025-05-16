"""Syntax highlighting service for code in notebooks."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from inklink.services.hcl_compiler import HCLCompiler
from inklink.services.drawj2d_service import Drawj2dService
from inklink.pipeline.processors.document_processor import DocumentService


@dataclass
class Token:
    """Represents a syntax token."""

    type: str
    value: str
    line: int
    column: int


@dataclass
class ThemeColors:
    """Color scheme for syntax highlighting."""

    background: str
    foreground: str
    keyword: str
    string: str
    comment: str
    number: str
    operator: str
    identifier: str
    function_name: str
    class_name: str

    @classmethod
    def monokai(cls) -> "ThemeColors":
        """Monokai theme colors."""
        return cls(
            background="#272822",
            foreground="#f8f8f2",
            keyword="#f92672",
            string="#e6db74",
            comment="#75715e",
            number="#ae81ff",
            operator="#f92672",
            identifier="#f8f8f2",
            function_name="#a6e22e",
            class_name="#a6e22e",
        )

    @classmethod
    def dark(cls) -> "ThemeColors":
        """Dark theme colors."""
        return cls(
            background="#1e1e1e",
            foreground="#d4d4d4",
            keyword="#569cd6",
            string="#ce9178",
            comment="#6a9955",
            number="#b5cea8",
            operator="#d4d4d4",
            identifier="#9cdcfe",
            function_name="#dcdcaa",
            class_name="#4ec9b0",
        )

    @classmethod
    def light(cls) -> "ThemeColors":
        """Light theme colors."""
        return cls(
            background="#ffffff",
            foreground="#000000",
            keyword="#0000ff",
            string="#a31515",
            comment="#008000",
            number="#098658",
            operator="#000000",
            identifier="#001080",
            function_name="#795e26",
            class_name="#267f99",
        )

    @classmethod
    def from_file(cls, file_path: Path) -> "ThemeColors":
        """Load theme from JSON file."""
        with open(file_path) as f:
            data = json.load(f)
        return cls(**data)


class SyntaxHighlightCompilerV2:
    """Compiles syntax highlighted code to HCL format."""

    def __init__(
        self, hcl_compiler: HCLCompiler = None, document_service: DocumentService = None
    ):
        self.hcl_compiler = hcl_compiler or HCLCompiler()
        self.document_service = document_service or DocumentService()
        self.themes_dir = Path("themes")
        self.themes_dir.mkdir(exist_ok=True)

    def compile(self, tokens: List[Token], theme_name: str = "monokai") -> str:
        """Compile tokens to HCL with syntax highlighting."""
        theme = self._load_theme(theme_name)
        drawj2d = Drawj2dService(self.hcl_compiler)

        # Group tokens by line
        lines: Dict[int, List[Token]] = {}
        for token in tokens:
            if token.line not in lines:
                lines[token.line] = []
            lines[token.line].append(token)

        # Start with document structure
        hcl_content = drawj2d._create_document_structure()

        # Add background
        bg_polygon = drawj2d._create_polygon(
            [(0, 0), (600, 0), (600, 800), (0, 800)], theme.background
        )
        hcl_content += drawj2d._add_draw_element("bg", bg_polygon)

        # Render each line
        y_offset = 50
        line_height = 20

        for line_num in sorted(lines.keys()):
            x_offset = 50
            line_tokens = sorted(lines[line_num], key=lambda t: t.column)

            for token in line_tokens:
                # Get color for token type
                color = self._get_token_color(token, theme)

                # Create text element
                text_elem = drawj2d._create_text(
                    token.value, x_offset, y_offset, color, 12  # font size
                )
                hcl_content += drawj2d._add_draw_element(
                    f"token_{line_num}_{token.column}", text_elem
                )

                # Update x offset (approximate char width)
                x_offset += len(token.value) * 7

            y_offset += line_height

        return hcl_content

    def _load_theme(self, theme_name: str) -> ThemeColors:
        """Load theme by name."""
        # Check built-in themes
        if theme_name == "monokai":
            return ThemeColors.monokai()
        elif theme_name == "dark":
            return ThemeColors.dark()
        elif theme_name == "light":
            return ThemeColors.light()

        # Check custom themes
        theme_file = self.themes_dir / f"{theme_name}.json"
        if theme_file.exists():
            return ThemeColors.from_file(theme_file)

        # Default to monokai
        return ThemeColors.monokai()

    def _get_token_color(self, token: Token, theme: ThemeColors) -> str:
        """Get color for token type."""
        color_map = {
            "keyword": theme.keyword,
            "string": theme.string,
            "comment": theme.comment,
            "number": theme.number,
            "operator": theme.operator,
            "identifier": theme.identifier,
            "function": theme.function_name,
            "class": theme.class_name,
        }
        return color_map.get(token.type, theme.foreground)
