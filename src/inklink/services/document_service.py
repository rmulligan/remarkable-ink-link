
"""Document creation service for Pi Share Receiver.

This service converts web content to reMarkable-compatible documents
using drawj2d to generate native reMarkable ink files.
"""

import os
import time
import json
import logging
import subprocess
import markdown
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List

# Use central configuration from inklink.config
from inklink.config import CONFIG

# Import utility functions for error handling
from inklink.utils import retry_operation, format_error

# Import Image for reading PNG dimensions
from PIL import Image

# Configure logging
logger = logging.getLogger(__name__)


class DocumentService:
    """Creates reMarkable documents from web content."""

    def __init__(self, temp_dir: str, drawj2d_path: str):
        """Initialize with directories and paths.

        Args:
            temp_dir: Directory for temporary files
            drawj2d_path: Path to drawj2d executable
        """
        self.temp_dir = temp_dir
        self.drawj2d_path = drawj2d_path
        os.makedirs(temp_dir, exist_ok=True)

        # Font configuration from central config - use Lines font for Remarkable
        self.heading_font = "Lines-Bold"
        self.body_font = "Lines"
        self.code_font = "Lines"

        # Remarkable Pro page size (portrait mode)
        self.page_width = 2160  # Updated for Remarkable Pro
        self.page_height = 1620  # Updated for Remarkable Pro
        self.margin = 120
        self.line_height = 40

    def create_hcl(
        self, url: str, qr_path: str, content: Dict[str, Any]
    ) -> Optional[str]:
        """Create HCL script from web content."""
        try:
            # Ensure we have valid content, even if minimal
            if not content:
                content = {"title": f"Page from {url}", "structured_content": []}

            logger.info(f"Creating HCL document for: {content.get('title', url)}")

            # Generate HCL file path
            hcl_filename = f"doc_{hash(url)}_{int(time.time())}.hcl"
            hcl_path = os.path.join(self.temp_dir, hcl_filename)

            with open(hcl_path, "w", encoding="utf-8") as f:
                # Set page size - use direct syntax based on drawj2d docs
                f.write(f'puts "size {self.page_width} {self.page_height}"\n\n')

                # Set font and pen
                f.write(f'puts "set_font {self.heading_font} 36"\n')
                f.write('puts "pen black"\n\n')

                # Set title position
                y_pos = self.margin

                # Add title
                title = content.get("title", "Untitled Document")
                f.write(
                    f'puts "text {self.margin} {y_pos} \\"{self._escape_hcl(title)}\\""\n'
                )
                # Space after title
                y_pos += self.line_height

                # Add URL under title
                f.write(f'puts "set_font {self.body_font} 20"\n')
                f.write(
                    f'puts "text {self.margin} {y_pos} \\"Source: {self._escape_hcl(url)}\\""\n'
                )
                y_pos += self.line_height

                # Add horizontal line separator
                f.write(
                    f'puts "line {self.margin} {y_pos} {self.page_width - self.margin} {y_pos} width=1.0"\n'
                )
                y_pos += self.line_height

                # Add QR code if available
                if os.path.exists(qr_path):
                    qr_size = 350
                    qr_x = self.page_width - self.margin - qr_size
                    f.write(
                        f'puts "rectangle {qr_x-5} {y_pos-5} {qr_size+10} {qr_size+10} width=1.0"\n'
                    )
                    f.write(
                        f'puts "image {qr_x} {y_pos} {qr_size} {qr_size} \\"{qr_path}\\""\n'
                    )

                # Process structured content
                y_pos += qr_size + self.line_height

                structured_content = content.get("structured_content", [])

                for item in structured_content:
                    item_type = item.get("type", "paragraph")
                    # Allow list items with 'items'
                    if item_type == "list" and item.get("items"):
                        for sub_item in item.get("items", []):
                            # Support list items as dicts or plain strings
                            if isinstance(sub_item, dict):
                                sub_item_content = sub_item.get("content", "")
                            else:
                                sub_item_content = str(sub_item)
                            if not sub_item_content:
                                continue
                            # Render each sub-item as a bullet point
                            f.write(
                                f'puts "text {self.margin + 20} {y_pos} \\"- {self._escape_hcl(sub_item_content)}\\""\n'
                            )
                            y_pos += self.line_height
                    else:
                        item_content = item.get("content", "")
                        if not item_content:
                            continue

                    # Check if we need a new page
                    if y_pos > (self.page_height - self.margin * 2):
                        f.write('puts "newpage"\n')
                        y_pos = self.margin

                    # Process based on content type
                    if item_type == "h1" or item_type == "heading":
                        f.write(f'puts "set_font {self.heading_font} 32"\n')
                        f.write(
                            f'puts "text {self.margin} {y_pos} \\"{self._escape_hcl(item_content)}\\""\n'
                        )
                        f.write(f'puts "set_font {self.body_font} 20"\n')
                        y_pos += self.line_height * 1.5
                    elif item_type == "h2":
                        f.write(f'puts "set_font {self.heading_font} 28"\n')
                        f.write(
                            f'puts "text {self.margin} {y_pos} \\"{self._escape_hcl(item_content)}\\""\n'
                        )
                        f.write(f'puts "set_font {self.body_font} 20"\n')
                        y_pos += self.line_height * 1.3
                    elif item_type == "h3" or item_type in ["h4", "h5", "h6"]:
                        f.write(f'puts "set_font {self.heading_font} 24"\n')
                        f.write(
                            f'puts "text {self.margin} {y_pos} \\"{self._escape_hcl(item_content)}\\""\n'
                        )
                        f.write(f'puts "set_font {self.body_font} 20"\n')
                        y_pos += self.line_height * 1.2
                    elif item_type == "code":
                        # Start code block
                        code_x = self.margin + 20
                        code_y = y_pos + self.line_height
                        code_lines = item_content.split("\n")
                        code_height = (
                            len(code_lines) * self.line_height + self.line_height
                        )

                        # Draw code block background and border
                        f.write(
                            f'puts "rectangle {self.margin} {y_pos} {self.page_width - self.margin*2} {code_height} width=1.0"\n'
                        )

                        # Process each line of code
                        f.write(f'puts "set_font {self.code_font} 18"\n')
                        for i, line in enumerate(code_lines):
                            line_y = code_y + (i * self.line_height)
                            f.write(
                                f'puts "text {code_x} {line_y} \\"{self._escape_hcl(line)}\\""\n'
                            )

                        f.write(f'puts "set_font {self.body_font} 20"\n')
                        y_pos += code_height + self.line_height
                    elif item_type == "list" or item_type == "bullet":
                        list_indent = 30

                        if item_type == "list" and "items" in item:
                            # Handle old-style list format
                            for list_item in item["items"]:
                                f.write(f'puts "text {self.margin} {y_pos} \\"• \\"\n')
                                f.write(
                                    f'puts "text {self.margin + list_indent} {y_pos} \\"{self._escape_hcl(list_item)}\\""\n'
                                )
                                y_pos += self.line_height
                        else:
                            # Handle single bullet point
                            f.write(f'puts "text {self.margin} {y_pos} \\"• \\"\n')
                            f.write(
                                f'puts "text {self.margin + list_indent} {y_pos} \\"{self._escape_hcl(item_content)}\\""\n'
                            )
                            y_pos += self.line_height
                    else:
                        # Default to paragraph
                        # Split long content into multiple lines if needed
                        max_chars_per_line = 85
                        paragraph_text = item_content

                        # Word wrap
                        words = paragraph_text.split()
                        current_line = ""

                        for word in words:
                            if len(current_line) + len(word) + 1 <= max_chars_per_line:
                                current_line += " " + word if current_line else word
                            else:
                                # Write the current line
                                f.write(
                                    f'puts "text {self.margin} {y_pos} \\"{self._escape_hcl(current_line)}\\""\n'
                                )
                                y_pos += self.line_height
                                current_line = word

                        # Write the last line if not empty
                        if current_line:
                            f.write(
                                f'puts "text {self.margin} {y_pos} \\"{self._escape_hcl(current_line)}\\""\n'
                            )
                            y_pos += self.line_height

                    # Add spacing between items
                    y_pos += self.line_height * 0.5

                # Add timestamp at the bottom of the last page
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(
                    f'puts "text {self.margin} {self.page_height - self.margin} \\"Generated: {timestamp}\\""\n'
                )

            logger.info(f"Created HCL file: {hcl_path}")
            # Log a preview for debugging
            with open(hcl_path, "r", encoding="utf-8") as f:
                hcl_preview = f.read(200)
                logger.info(f"HCL preview (first 200 chars): {hcl_preview}")

            return hcl_path
        except Exception as e:
            logger.error(f"Error creating HCL document: {e}")
            return None

    def create_pdf_hcl(
        self, pdf_path: str, title: str, qr_path: str = None, images: List[str] = None
    ) -> Optional[str]:
        """Create HCL script for PDF file."""
        try:
            logger.info(f"Creating HCL document for PDF: {pdf_path}")

            # Generate HCL file path
            hcl_filename = f"pdf_{hash(pdf_path)}_{int(time.time())}.hcl"
            hcl_path = os.path.join(self.temp_dir, hcl_filename)

            with open(hcl_path, "w", encoding="utf-8") as f:
                # Set page size - use direct syntax based on drawj2d docs
                f.write(f'puts "size {self.page_width} {self.page_height}"\n\n')

                # Set font and pen
                f.write(f'puts "set_font {self.heading_font} 36"\n')
                f.write('puts "pen black"\n\n')

                # Set title position
                y_pos = self.margin

                # Add title
                f.write(
                    f'puts "text {self.margin} {y_pos} \\"{self._escape_hcl(title)}\\""\n'
                )
                y_pos += self.line_height * 1.5

                # Add URL under title
                f.write(f'puts "set_font {self.body_font} 20"\n')
                f.write(
                    f'puts "text {self.margin} {y_pos} \\"Source: {self._escape_hcl(os.path.basename(pdf_path))}\\""\n'
                )
                y_pos += self.line_height

                # Add horizontal line separator
                f.write(
                    f'puts "line {self.margin} {y_pos} {self.page_width - self.margin} {y_pos} width=1.0"\n'
                )
                y_pos += self.line_height * 2

                # Add QR code if available
                if qr_path and os.path.exists(qr_path):
                    qr_size = 350
                    qr_x = self.page_width - self.margin - qr_size
                    f.write(
                        f'puts "rectangle {qr_x-5} {y_pos-5} {qr_size+10} {qr_size+10} width=1.0"\n'
                    )
                    f.write(
                        f'puts "image {qr_x} {y_pos} {qr_size} {qr_size} \\"{qr_path}\\""\n'
                    )
                    y_pos += qr_size + self.line_height

                # Embed raster images if provided
                if images:
                    for img_path in images:
                        f.write('puts "newpage"\n')
                        with Image.open(img_path) as img:
                            orig_w, orig_h = img.size
                        max_w = self.page_width - 2 * self.margin
                        scale = max_w / orig_w
                        width = int(orig_w * scale)
                        height = int(orig_h * scale)
                        x = self.margin
                        y = self.margin
                        f.write(
                            f'puts "image {x} {y} {width} {height} \\"{img_path}\\""\n'
                        )
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(
                        f'puts "text {self.margin} {self.page_height - self.margin} \\"Generated: {timestamp}\\""\n'
                    )
                    return hcl_path

                # Add instructions for viewing the PDF
                f.write(
                    f'puts "text {self.margin} {y_pos} \\"This document has been converted to Remarkable format.\\""\n'
                )
                y_pos += self.line_height
                f.write(
                    f'puts "text {self.margin} {y_pos} \\"Original PDF: {self._escape_hcl(os.path.basename(pdf_path))}\\""\n'
                )

                # Add timestamp at the bottom of the page
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(
                    f'puts "text {self.margin} {self.page_height - self.margin} \\"Generated: {timestamp}\\""\n'
                )

            logger.info(f"Created HCL file for PDF: {hcl_path}")
            return hcl_path
        except Exception as e:
            logger.error(f"Error creating HCL document for PDF: {e}")
            return None

    def create_rmdoc(self, hcl_path: str, url: str) -> Optional[str]:
        """Convert HCL to Remarkable document."""
        try:
            timestamp = int(time.time())
            rm_filename = f"rm_{hash(url)}_{timestamp}.rm"
            rm_path = os.path.join(self.temp_dir, rm_filename)

            return self._convert_to_remarkable(hcl_path, rm_path)
        except Exception as e:
            logger.error(f"Error in create_rmdoc: {e}")
            return None

    def _convert_to_remarkable(self, hcl_path: str, rm_path: str) -> Optional[str]:
        """Convert HCL file to Remarkable format using drawj2d."""
        try:
            logger.info(f"Starting conversion from {hcl_path} to {rm_path}")

            # Input validation
            if not os.path.exists(hcl_path):
                error_msg = format_error("input", "HCL file not found", hcl_path)
                logger.error(error_msg)
                return None

            # Always attempt real conversion via drawj2d
            # (Stub branch removed to ensure conversion is attempted in tests)

            # Double check file contents
            try:
                with open(hcl_path, "r") as f:
                    hcl_content = f.read(500)
                    logger.info(
                        f"HCL file content (first 500 chars): {hcl_content[:500]}"
                    )
            except Exception as e:
                logger.error(f"Failed to read HCL file: {e}")

            # Check output path
            output_dir = os.path.dirname(rm_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)

            # Use parameters for Remarkable format - fixed to not use `-r229` flag
            # -Trm: Target is Remarkable
            # -o: Specify output file
            # -rmv6: Use rmv6 format introduced in Remarkable firmware 3.0
            cmd = [self.drawj2d_path, "-Trm", "-rmv6", "-o", rm_path, hcl_path]
            logger.info(f"Conversion command: {' '.join(cmd)}")

            # Define the conversion function that will be retried if it fails
            def run_conversion(cmd_args):
                logger.info(f"Running drawj2d conversion: {' '.join(cmd_args)}")

                # Running the conversion using subprocess.run for better error handling
                result = subprocess.run(cmd_args, capture_output=True, text=True)
                logger.info(f"Command stdout: {result.stdout}")
                logger.info(f"Command stderr: {result.stderr}")

                if result.returncode != 0:
                    raise RuntimeError(
                        f"drawj2d conversion failed: Exit code {result.returncode}, stderr: {result.stderr}"
                    )

                if not os.path.exists(rm_path):
                    logger.error(
                        f"Output file missing: {rm_path}, even though command reported success"
                    )
                    raise FileNotFoundError(
                        f"Expected output file not created: {rm_path}"
                    )
                else:
                    file_size = os.path.getsize(rm_path)
                    logger.info(
                        f"Output file successfully created: {rm_path} ({file_size} bytes)"
                    )
                    if file_size < 50:
                        logger.error(
                            f"Output file size is suspiciously small: {file_size} bytes. Possible conversion error."
                        )
                        raise ValueError(f"Output file too small: {file_size} bytes")
                    with open(rm_path, "rb") as rf:
                        preview = rf.read(100)
                    logger.info(f"Output file preview (first 100 bytes): {preview}")

                return rm_path

            # Use retry operation for running the conversion
            return retry_operation(
                run_conversion,
                cmd,
                operation_name="Document conversion",
                max_retries=2,  # Only retry a couple of times for conversion
            )
        except Exception as e:
            logger.error(
                format_error(
                    "conversion", "Failed to convert document to Remarkable format", e
                )
            )
            return None

    def _escape_hcl(self, text: str) -> str:
        """Escape special characters for HCL."""
        if not text:
            return ""
        return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

    def _process_content(self, content: Dict[str, Any]) -> str:
        """Process content dictionary into plain text.

        Args:
            content: Dictionary containing either structured_content or raw content

        Returns:
            Processed plain text with proper formatting
        """
        plain_content = ""

        if structured_content := content.get("structured_content", []):
            for item in structured_content:
                content_type = item.get("type", "paragraph")
                text = item.get("content", "")

                if content_type.startswith("h"):
                    plain_content += f"{text}\n\n"  # No markdown-style heading
                elif content_type == "paragraph":
                    plain_content += f"{text}\n\n"
                elif content_type == "code":
                    plain_content += f"{text}\n\n"  # No code block markers
                elif content_type == "list" and "items" in item:
                    for list_item in item["items"]:
                        plain_content += f"• {list_item}\n"
                    plain_content += "\n"
                elif content_type == "bullet":
                    plain_content += f"• {text}\n\n"
        else:
            plain_content = content.get("content", "")
            if plain_content and "<" in plain_content and ">" in plain_content:
                plain_content = self._html_to_text(plain_content)

        return plain_content

    def _html_to_text(self, html_content: str) -> str:
        """Extract text content from HTML, preserving structure."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style"]):
                element.extract()

            # Get text
            text = soup.get_text()

            # Break into lines and remove leading/trailing space
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Remove blank lines and join with double newlines for paragraphs
            return "\n\n".join(chunk for chunk in chunks if chunk)
        except Exception as e:
            logger.error(f"Error converting HTML to text: {e}")
            return html_content
