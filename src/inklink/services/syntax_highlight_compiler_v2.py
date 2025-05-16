"""Enhanced syntax highlighting compiler with layout support for Phase 4."""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .syntax_highlight_compiler import Language, SyntaxHighlightCompiler, Theme
from .syntax_layout import (
    CodeMetadata,
    FontMetrics,
    LayoutCalculator,
    LineLayout,
    Margins,
    PageLayout,
    PageSize,
)
from .syntax_tokens import TokenType

# HCLRenderer will be implemented internally

logger = logging.getLogger(__name__)


@dataclass
class RenderOptions:
    """Options for rendering syntax-highlighted code."""

    show_line_numbers: bool = True
    show_metadata: bool = True
    embed_metadata: bool = True  # embed in HCL output
    page_size: PageSize = PageSize.REMARKABLE_2
    margins: Optional[Margins] = None
    font_metrics: Optional[FontMetrics] = None
    theme: Theme = Theme.MONOKAI
    debug_mode: bool = False


class SyntaxHighlightCompilerV2(SyntaxHighlightCompiler):
    """Enhanced compiler with layout and metadata support."""

    def __init__(self, options: Optional[RenderOptions] = None):
        super().__init__()
        self.options = options or RenderOptions()
        self.layout_calculator = LayoutCalculator(
            page_size=self.options.page_size,
            margins=self.options.margins,
            font_metrics=self.options.font_metrics,
            show_line_numbers=self.options.show_line_numbers,
            show_metadata=self.options.show_metadata,
        )
        self.set_theme(self.options.theme.value)

    def _get_token_color(self, token_type: TokenType) -> str:
        """Get color for a token type from current theme."""
        if token_type in self.current_theme.colors:
            return self.current_theme.colors[token_type]
        return "0x000000"  # Default black for unknown types

    def compile_with_layout(
        self,
        code: str,
        language: Language = Language.JAVASCRIPT,
        metadata: Optional[CodeMetadata] = None,
    ) -> List[Dict[str, Any]]:
        """Compile code with full layout support, returning HCL per page."""
        # Tokenize the code
        self.set_language(language.value)
        tokens = self.tokenize(code)

        # Split into lines
        lines = code.split("\n")

        # Calculate layout
        pages = self.layout_calculator.calculate_layout(lines, metadata)

        # Generate HCL for each page
        hcl_pages = []
        for page in pages:
            page_hcl = self._render_page(page, tokens, lines)
            hcl_pages.append(
                {
                    "page_number": page.page_number,
                    "hcl": page_hcl,
                    "metadata": (
                        self._extract_page_metadata(page)
                        if self.options.embed_metadata
                        else None
                    ),
                }
            )

        return hcl_pages

    def _render_page(self, page: PageLayout, tokens: List, lines: List[str]) -> str:
        """Render a single page to HCL."""
        hcl_content = [f"# Page {page.page_number}", f"page_size = [{page.page_size.width}, {page.page_size.height}]", "", self._render_code_lines(page, tokens, lines)]

        # Add debug grid if enabled
        if self.options.debug_mode:
            hcl_content.append(self._generate_debug_grid(page))

        # Render header/metadata if present
        if page.page_number == 1 and self.options.show_metadata and page.metadata:
            hcl_content.append(self._render_header(page))

        # Render line numbers
        if self.options.show_line_numbers:
            hcl_content.append(self._render_line_numbers(page))

        # Add metadata comment if embedding
        if self.options.embed_metadata:
            hcl_content.append(self._embed_metadata_comment(page))

        return "\n".join(hcl_content)

    def _render_header(self, page: PageLayout) -> str:
        """Render metadata header."""
        header_lines = []
        metadata = page.metadata

        if not metadata:
            return ""

        # Find header region
        header_region = next(
            (r for r in page.regions if r.content_type == "header"), None
        )
        if not header_region:
            return ""

        y_pos = header_region.y

        # Render filename
        if metadata.filename:
            header_lines.append(f'text "{metadata.filename}" {{')
            header_lines.append(f"  x = {header_region.x}")
            header_lines.append(f"  y = {y_pos}")
            header_lines.append('  color = "0x333333"')
            header_lines.append(
                f"  size = {int(self.layout_calculator.font_metrics.size * 1.2)}"
            )
            header_lines.append("}")
            y_pos += self.layout_calculator.font_metrics.actual_line_height

        # Render language
        if metadata.language:
            header_lines.append(f'text "Language: {metadata.language}" {{')
            header_lines.append(f"  x = {header_region.x}")
            header_lines.append(f"  y = {y_pos}")
            header_lines.append('  color = "0x666666"')
            header_lines.append(f"  size = {self.layout_calculator.font_metrics.size}")
            header_lines.append("}")
            y_pos += self.layout_calculator.font_metrics.actual_line_height

        # Render author
        if metadata.author:
            header_lines.append(f'text "Author: {metadata.author}" {{')
            header_lines.append(f"  x = {header_region.x}")
            header_lines.append(f"  y = {y_pos}")
            header_lines.append('  color = "0x666666"')
            header_lines.append(f"  size = {self.layout_calculator.font_metrics.size}")
            header_lines.append("}")

        return "\n".join(header_lines)

    def _render_line_numbers(self, page: PageLayout) -> str:
        """Render line numbers for the page."""
        line_number_lines = []

        # Find line numbers region
        ln_region = next(
            (r for r in page.regions if r.content_type == "line_numbers"), None
        )
        if not ln_region:
            return ""

        for line in page.lines:
            if line.has_line_number:
                line_number_lines.append(f'text "{line.line_number}" {{')
                line_number_lines.append(
                    f"  x = {ln_region.x + ln_region.width - 30}"
                )  # right-align
                line_number_lines.append(f"  y = {line.y}")
                line_number_lines.append('  color = "0x999999"')
                line_number_lines.append(
                    f"  size = {int(self.layout_calculator.font_metrics.size * 0.9)}"
                )
                line_number_lines.append("}")

        return "\n".join(line_number_lines)

    def _render_code_lines(
        self, page: PageLayout, tokens: List, lines: List[str]
    ) -> str:
        """Render syntax-highlighted code lines."""
        code_lines = []

        # Create line-to-tokens mapping
        line_tokens = self._map_tokens_to_lines(tokens, lines)

        for line_layout in page.lines:
            line_num = line_layout.line_number - 1  # 0-indexed
            if line_num < len(lines):
                # Get tokens for this line
                if line_num in line_tokens:
                    code_lines.append(
                        self._render_highlighted_line(
                            line_layout, line_tokens[line_num], lines[line_num]
                        )
                    )
                else:
                    # No tokens, render as plain text
                    code_lines.append(f'text "{line_layout.text}" {{')
                    code_lines.append(f"  x = {line_layout.x}")
                    code_lines.append(f"  y = {line_layout.y}")
                    code_lines.append('  color = "0x000000"')
                    code_lines.append(
                        f"  size = {self.layout_calculator.font_metrics.size}"
                    )
                    code_lines.append("}")

        return "\n".join(code_lines)

    def _render_highlighted_line(
        self, line_layout: LineLayout, tokens: List, original_text: str
    ) -> str:
        """Render a line with syntax highlighting."""
        hcl_parts = []
        x_offset = line_layout.x

        for token in tokens:
            color = self._get_token_color(token.type)
            hcl_parts.append(f'text "{token.value}" {{')
            hcl_parts.append(f"  x = {x_offset}")
            hcl_parts.append(f"  y = {line_layout.y}")
            hcl_parts.append(f'  color = "{color}"')
            hcl_parts.append(f"  size = {self.layout_calculator.font_metrics.size}")
            hcl_parts.append("}")

            # Update x offset for next token
            x_offset += self.layout_calculator.font_metrics.measure_text(token.value)

        return "\n".join(hcl_parts)

    @staticmethod
    def _map_tokens_to_lines(tokens: List, lines: List[str]) -> Dict[int, List]:
        """Map tokens to their line numbers."""
        line_tokens = {}
        current_line = 0
        current_col = 0

        for token in tokens:
            # Add to current line
            if current_line not in line_tokens:
                line_tokens[current_line] = []
            line_tokens[current_line].append(token)

            # Update position
            if token.type.name == "NEWLINE" or "\n" in token.value:
                current_line += token.value.count("\n")
                current_col = 0
            else:
                current_col += len(token.value)

        return line_tokens

    @staticmethod
    def _generate_debug_grid(page: PageLayout) -> str:
        """Generate debug grid for testing."""
        grid_lines = ["# Debug grid", "rectangle {{", f"  x = {page.margins.left}", f"  y = {page.margins.top}", f"  width = {page.content_width}", f"  height = {page.content_height}", '  stroke = "0xFF0000"', "  stroke_width = 2", '  fill = "none"', "}"]

        # Draw regions
        for region in page.regions:
            color = {
                "header": "0x00FF00",
                "line_numbers": "0x0000FF",
                "code": "0xFF00FF",
            }.get(region.content_type, "0x000000")

            grid_lines.append("rectangle {{")
            grid_lines.append(f"  x = {region.x}")
            grid_lines.append(f"  y = {region.y}")
            grid_lines.append(f"  width = {region.width}")
            grid_lines.append(f"  height = {region.height}")
            grid_lines.append(f'  stroke = "{color}"')
            grid_lines.append("  stroke_width = 1")
            grid_lines.append('  fill = "none"')
            grid_lines.append("}")

        return "\n".join(grid_lines)

    @staticmethod
    def _embed_metadata_comment(page: PageLayout) -> str:
        """Embed metadata as HCL comment."""
        if not page.metadata:
            return ""

        metadata_dict = {
            "filename": page.metadata.filename,
            "language": page.metadata.language,
            "line_start": page.metadata.line_start,
            "line_end": page.metadata.line_end,
            "author": page.metadata.author,
            "tags": page.metadata.tags,
            "page": page.page_number,
        }

        # Remove None values
        metadata_dict = {k: v for k, v in metadata_dict.items() if v is not None}

        return f"# METADATA: {json.dumps(metadata_dict)}"

    @staticmethod
    def _extract_page_metadata(page: PageLayout) -> Dict[str, Any]:
        """Extract metadata for a page."""
        return {
            "page_number": page.page_number,
            "line_count": len(page.lines),
            "regions": [
                {"type": r.content_type, "bounds": r.bounds} for r in page.regions
            ],
        }
