"""Layout calculator for syntax highlighting with advanced formatting."""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class PageSize(Enum):
    """Standard page sizes for reMarkable devices."""

    REMARKABLE_2 = (1404, 1872)  # pixels
    REMARKABLE_PRO = (1872, 2580)  # pixels

    @property
    def width(self) -> int:
        return self.value[0]

    @property
    def height(self) -> int:
        return self.value[1]


@dataclass
class Margins:
    """Page margins in pixels."""

    top: int = 100
    bottom: int = 100
    left: int = 80
    right: int = 80


@dataclass
class FontMetrics:
    """Font measurement properties."""

    size: int = 24  # base font size
    line_height: float = 1.4  # multiplier for line spacing
    char_width: float = 0.6  # average character width as ratio of font size

    @property
    def actual_line_height(self) -> int:
        """Calculate actual line height in pixels."""
        return int(self.size * self.line_height)

    @property
    def avg_char_width(self) -> int:
        """Calculate average character width in pixels."""
        return int(self.size * self.char_width)

    def measure_text(self, text: str) -> int:
        """Measure the width of text in pixels."""
        return len(text) * self.avg_char_width


@dataclass
class CodeMetadata:
    """Metadata for code sections."""

    filename: Optional[str] = None
    language: Optional[str] = None
    line_start: int = 1
    line_end: Optional[int] = None
    timestamp: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class LayoutRegion:
    """Represents a region on the page."""

    x: int
    y: int
    width: int
    height: int
    content_type: str = "code"  # code, line_numbers, metadata, header

    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Return (x1, y1, x2, y2) bounds."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class LineLayout:
    """Layout for a single line of code."""

    line_number: int
    text: str
    x: int
    y: int
    width: int
    height: int
    wrapped: bool = False
    continuation_of: Optional[int] = (
        None  # line number if this is a wrapped continuation
    )

    @property
    def has_line_number(self) -> bool:
        """Check if this line should display a line number."""
        return not self.wrapped or self.continuation_of is None


@dataclass
class PageLayout:
    """Complete layout for a page."""

    page_number: int
    page_size: PageSize
    margins: Margins
    regions: List[LayoutRegion] = field(default_factory=list)
    lines: List[LineLayout] = field(default_factory=list)
    metadata: Optional[CodeMetadata] = None

    @property
    def content_width(self) -> int:
        """Available width for content."""
        return self.page_size.width - self.margins.left - self.margins.right

    @property
    def content_height(self) -> int:
        """Available height for content."""
        return self.page_size.height - self.margins.top - self.margins.bottom

    @property
    def code_region(self) -> Optional[LayoutRegion]:
        """Get the main code region."""
        for region in self.regions:
            if region.content_type == "code":
                return region
        return None


class LayoutCalculator:
    """Calculate optimal layout for syntax-highlighted code."""

    def __init__(
        self,
        page_size: PageSize = PageSize.REMARKABLE_2,
        margins: Optional[Margins] = None,
        font_metrics: Optional[FontMetrics] = None,
        show_line_numbers: bool = True,
        show_metadata: bool = True,
    ):
        self.page_size = page_size
        self.margins = margins or Margins()
        self.font_metrics = font_metrics or FontMetrics()
        self.show_line_numbers = show_line_numbers
        self.show_metadata = show_metadata
        self._line_number_width = 0

    def calculate_layout(
        self,
        lines: List[str],
        metadata: Optional[CodeMetadata] = None,
        start_page: int = 1,
    ) -> List[PageLayout]:
        """Calculate complete layout for code across multiple pages."""
        pages = []
        current_page = start_page
        remaining_lines = list(enumerate(lines, start=1))

        while remaining_lines:
            page = self._create_page(current_page, metadata)
            remaining_lines = self._layout_page(page, remaining_lines, metadata)
            pages.append(page)
            current_page += 1

        return pages

    def _create_page(
        self, page_number: int, metadata: Optional[CodeMetadata]
    ) -> PageLayout:
        """Create a new page with regions."""
        page = PageLayout(
            page_number=page_number,
            page_size=self.page_size,
            margins=self.margins,
            metadata=metadata,
        )

        # Calculate regions
        current_y = self.margins.top

        # Header region (if first page and metadata exists)
        if page_number == 1 and self.show_metadata and metadata:
            header_height = self._calculate_header_height(metadata)
            page.regions.append(
                LayoutRegion(
                    x=self.margins.left,
                    y=current_y,
                    width=page.content_width,
                    height=header_height,
                    content_type="header",
                )
            )
            current_y += header_height + 20  # spacing

        # Line numbers region
        if self.show_line_numbers:
            self._line_number_width = self._calculate_line_number_width(metadata)
            page.regions.append(
                LayoutRegion(
                    x=self.margins.left,
                    y=current_y,
                    width=self._line_number_width,
                    height=page.content_height - (current_y - self.margins.top),
                    content_type="line_numbers",
                )
            )

        # Code region
        code_x = self.margins.left + (
            self._line_number_width + 20 if self.show_line_numbers else 0
        )
        code_width = self.page_size.width - code_x - self.margins.right
        page.regions.append(
            LayoutRegion(
                x=code_x,
                y=current_y,
                width=code_width,
                height=page.content_height - (current_y - self.margins.top),
                content_type="code",
            )
        )

        return page

    def _layout_page(
        self,
        page: PageLayout,
        remaining_lines: List[Tuple[int, str]],
        metadata: Optional[CodeMetadata],
    ) -> List[Tuple[int, str]]:
        """Layout lines on a page, return remaining lines."""
        code_region = page.code_region
        if not code_region:
            return remaining_lines

        current_y = code_region.y
        max_y = code_region.y + code_region.height
        line_height = self.font_metrics.actual_line_height

        while remaining_lines and current_y + line_height <= max_y:
            line_num, text = remaining_lines[0]

            # Check if line needs wrapping
            line_width = self.font_metrics.measure_text(text)
            if line_width > code_region.width:
                # Wrap line
                wrapped_lines = self._wrap_line(text, code_region.width)
                for i, wrapped_text in enumerate(wrapped_lines):
                    if current_y + line_height > max_y:
                        break

                    page.lines.append(
                        LineLayout(
                            line_number=line_num,
                            text=wrapped_text,
                            x=code_region.x,
                            y=current_y,
                            width=code_region.width,
                            height=line_height,
                            wrapped=i > 0,
                            continuation_of=line_num if i > 0 else None,
                        )
                    )
                    current_y += line_height

                if current_y + line_height <= max_y:
                    remaining_lines.pop(0)
            else:
                # Fits on one line
                page.lines.append(
                    LineLayout(
                        line_number=line_num,
                        text=text,
                        x=code_region.x,
                        y=current_y,
                        width=code_region.width,
                        height=line_height,
                    )
                )
                current_y += line_height
                remaining_lines.pop(0)

        return remaining_lines

    def _wrap_line(self, text: str, max_width: int) -> List[str]:
        """Wrap a line of text to fit within max_width."""
        if not text:
            return [""]

        words = text.split(" ")
        lines = []
        current_line = []
        current_width = 0

        for word in words:
            word_width = self.font_metrics.measure_text(word + " ")
            if current_width + word_width > max_width and current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_width = word_width
            else:
                current_line.append(word)
                current_width += word_width

        if current_line:
            lines.append(" ".join(current_line))

        # If still too long, break by characters
        final_lines = []
        for line in lines:
            if self.font_metrics.measure_text(line) > max_width:
                # Character-level breaking
                chars_per_line = max_width // self.font_metrics.avg_char_width
                for i in range(0, len(line), chars_per_line):
                    final_lines.append(line[i : i + chars_per_line])
            else:
                final_lines.append(line)

        return final_lines

    def _calculate_line_number_width(self, metadata: Optional[CodeMetadata]) -> int:
        """Calculate width needed for line numbers."""
        if not self.show_line_numbers:
            return 0

        # Estimate max line number
        max_line = metadata.line_end if metadata and metadata.line_end else 999
        digits = len(str(max_line))
        return (digits + 1) * self.font_metrics.avg_char_width + 20  # padding

    def _calculate_header_height(self, metadata: CodeMetadata) -> int:
        """Calculate height needed for metadata header."""
        lines = 0
        if metadata.filename:
            lines += 1
        if metadata.language:
            lines += 1
        if metadata.author:
            lines += 1
        if metadata.tags:
            lines += 1

        return lines * self.font_metrics.actual_line_height + 20  # padding
