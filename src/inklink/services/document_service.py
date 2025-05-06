
"""Document conversion service for InkLink.

This service handles conversion of web content to reMarkable-compatible documents
using RCU (reMarkable Content Uploader) for direct conversion to .rm files.
"""

import os
import time
import json
import logging
import tempfile
import markdown
from typing import Dict, Any, Optional, List

# Import utility functions for error handling and RCU integration
from inklink.utils import (
    retry_operation, 
    format_error,
    ensure_rcu_available,
    convert_markdown_to_rm,
    convert_html_to_rm
)

# Use central configuration from inklink.config
from inklink.config import CONFIG

logger = logging.getLogger(__name__)


# Structured content schema (multi-page support):
# structured_content = [
#     {
#         "page_number": 1,
#         "items": [
#             {"type": "heading", "content": "Section 1"},
#             {"type": "paragraph", "content": "Text..."},
#             ...
#         ],
#         "metadata": {...}
#     },
#     {
#         "page_number": 2,
#         "items": [
#             ...
#         ],
#         "metadata": {...}
#     },
#     ...
# ]
class DocumentService:
    """Creates reMarkable documents from web content."""

    def __init__(self, temp_dir: str, drawj2d_path: Optional[str] = None, pdf_service=None):
        """
        Initialize with directories and paths.

        Args:
            temp_dir: Directory for temporary files
            drawj2d_path: Optional path to drawj2d executable (for legacy support)
            pdf_service: Optional PDFService instance for index notebook updates
        """
        self.temp_dir = temp_dir
        self.drawj2d_path = drawj2d_path
        self.pdf_service = pdf_service  # Used for automated index notebook updates
        os.makedirs(temp_dir, exist_ok=True)

        # Check if RCU is available
        self.use_rcu = ensure_rcu_available()
        if not self.use_rcu:
            logger.warning(
                "RCU not available, falling back to drawj2d. "
                "Install RCU for better conversion quality."
            )
            if not drawj2d_path or not os.path.exists(drawj2d_path):
                logger.error(
                    "drawj2d fallback path not available. Document conversion will fail."
                )

        # Determine Remarkable model ("pro" or "rm2")
        rm_model = CONFIG.get("REMARKABLE_MODEL", "pro").lower()
        self.is_remarkable_pro = (rm_model == "pro")
        # Page dimensions (pixels) and layout defaults
        # These defaults match the Pro configuration; adjust if rm2
        self.page_width = CONFIG.get("PAGE_WIDTH", 2160)
        self.page_height = CONFIG.get("PAGE_HEIGHT", 1620)
        self.margin = CONFIG.get("PAGE_MARGIN", 120)
        self.line_height = 40
        
        # Set font settings from CONFIG
        self.heading_font = CONFIG.get("HEADING_FONT", "Liberation Sans")
        self.body_font = CONFIG.get("BODY_FONT", "Liberation Sans")
        self.code_font = CONFIG.get("CODE_FONT", "DejaVu Sans Mono")

    def create_rmdoc_from_content(
        self, url: str, qr_path: str, content: Dict[str, Any]
    ) -> Optional[str]:
        """
        Create reMarkable document from structured content, supporting cross-page links.

        This function renders the structured content (with per-page items, metadata, and cross-page links)
        to markdown and then uses RCU to convert it to reMarkable format.

        Args:
            url: Source URL for reference
            qr_path: Path to QR code image
            content: Structured content dictionary. Supports both legacy and enhanced formats:
                - Legacy: {"structured_content": [ ... ]}
                - Enhanced: {"pages": [...], "cross_page_links": [...]}

        Returns:
            Path to generated .rm file or None if failed
        """
        import logging
        logger = logging.getLogger("inklink.document_service")
        try:
            # Ensure we have valid content
            if not content:
                content = {"title": f"Page from {url}", "structured_content": []}

            logger.info(f"Creating document for: {content.get('title', url)}")

            # Detect enhanced format (pages/cross_page_links) or legacy (structured_content)
            pages = content.get("pages")
            cross_page_links = content.get("cross_page_links")
            if pages is None:
                # Fallback to legacy
                pages = content.get("structured_content", [])
                cross_page_links = content.get("cross_page_links", [])

            # Generate markdown file
            md_filename = f"doc_{hash(url)}_{int(time.time())}.md"
            md_path = os.path.join(self.temp_dir, md_filename)
            logger.debug(f"Writing markdown file to {md_path}")

            



            with open(md_path, "w", encoding="utf-8") as f:
                # Add title
                title = content.get("title", "Untitled Document")
                f.write(f"# {title}\n\n")

                # Add source URL
                f.write(f"Source: {url}\n\n")

                # Add horizontal separator
                f.write("---\n\n")

                # Add QR code if available
                if os.path.exists(qr_path):
                    logger.debug(f"QR code found at {qr_path}, adding to markdown")
                    f.write(f"![QR Code for original content]({qr_path})\n\n")
                else:
                    logger.debug(f"No QR code found at {qr_path}")

                # If raw_markdown is present, write it directly and skip structured_content
                raw_markdown = content.get("raw_markdown")
                if raw_markdown:
                    f.write(raw_markdown)
                    if not raw_markdown.endswith("\n"):
                        f.write("\n")
                else:

                    # Render cross-page links section if present
                    if cross_page_links:
                        f.write("## Cross-Page Links\n\n")
                        for link in cross_page_links:
                            from_page = link.get("from_page")
                            to_page = link.get("to_page")
                            label = link.get("label", f"Link from page {from_page} to {to_page}")
                            link_type = link.get("type", "")
                            f.write(f"- {label} (from page {from_page} to page {to_page}, type: {link_type})\n")
                        f.write("\n---\n\n")

                    # Process pages (multi-page aware)
                    for idx, page in enumerate(pages):
                        page_number = page.get("page_number", idx + 1)
                        items = page.get("items", [])
                        metadata = page.get("metadata", {})

                        # Write page break except for first page
                        if page_number and page_number > 1:
                            f.write("\n---\n\n")

                        # Optionally, write page header/footer using metadata
                        # Annotate references if present in metadata
                        references = metadata.get("references", [])
                        if references:
                            f.write("**References on this page:**\n")
                            for ref in references:
                                ref_label = ref.get("label", "")
                                ref_to = ref.get("to_page", "")
                                ref_type = ref.get("type", "")
                                f.write(f"- {ref_label} (to page {ref_to}, type: {ref_type})\n")
                            f.write("\n")

                        for item in items:
                            item_type = item.get("type", "paragraph")
                            item_content = item.get("content", "")

                            if not item_content:
                                continue

                            if item_type == "h1" or item_type == "heading":
                                f.write(f"# {item_content}\n\n")
                            elif item_type == "h2":
                                f.write(f"## {item_content}\n\n")
                            elif item_type == "h3":
                                f.write(f"### {item_content}\n\n")
                            elif item_type in ["h4", "h5", "h6"]:
                                f.write(f"#### {item_content}\n\n")
                            elif item_type == "code":
                                f.write(f"```\n{item_content}\n```\n\n")
                            elif item_type == "math":
                                f.write(f"$$\n{item_content}\n$$\n\n")
                            elif item_type == "diagram":
                                f.write(f"```mermaid\n{item_content}\n```\n\n")
                            elif item_type == "list" and "items" in item:
                                for list_item in item["items"]:
                                    f.write(f"* {list_item}\n")
                                f.write("\n")
                            elif item_type == "bullet":
                                f.write(f"* {item_content}\n\n")
                            elif item_type == "image" and "url" in item:
                                caption = item.get("caption", "")
                                if caption:
                                    f.write(f"![{caption}]({item['url']})\n\n")
                                else:
                                    f.write(f"![]({item['url']})\n\n")
                            else:
                                # Default to paragraph
                                f.write(f"{item_content}\n\n")

                    # Render cross-page links section if present
                    if cross_page_links:
                        f.write("## Cross-Page Links\n\n")
                        for link in cross_page_links:
                            from_page = link.get("from_page")
                            to_page = link.get("to_page")
                            label = link.get("label", f"Link from page {from_page} to {to_page}")
                            link_type = link.get("type", "")
                            f.write(f"- {label} (from page {from_page} to page {to_page}, type: {link_type})\n")
                        f.write("\n---\n\n")

                    # Process pages (multi-page aware)
                    for idx, page in enumerate(pages):
                        page_number = page.get("page_number", idx + 1)
                        items = page.get("items", [])
                        metadata = page.get("metadata", {})

                        # Write page break except for first page
                        if page_number and page_number > 1:
                            f.write("\n---\n\n")

                        # Optionally, write page header/footer using metadata
                        # Annotate references if present in metadata
                        references = metadata.get("references", [])
                        if references:
                            f.write("**References on this page:**\n")
                            for ref in references:
                                ref_label = ref.get("label", "")
                                ref_to = ref.get("to_page", "")
                                ref_type = ref.get("type", "")
                                f.write(f"- {ref_label} (to page {ref_to}, type: {ref_type})\n")
                            f.write("\n")

                        for item in items:
                            item_type = item.get("type", "paragraph")
                            item_content = item.get("content", "")

                            if not item_content:
                                continue

                            if item_type == "h1" or item_type == "heading":
                                f.write(f"# {item_content}\n\n")
                            elif item_type == "h2":
                                f.write(f"## {item_content}\n\n")
                            elif item_type == "h3":
                                f.write(f"### {item_content}\n\n")
                            elif item_type in ["h4", "h5", "h6"]:
                                f.write(f"#### {item_content}\n\n")
                            elif item_type == "code":
                                f.write(f"```\n{item_content}\n```\n\n")
                            elif item_type == "math":
                                f.write(f"$$\n{item_content}\n$$\n\n")
                            elif item_type == "diagram":
                                f.write(f"```mermaid\n{item_content}\n```\n\n")
                            elif item_type == "list" and "items" in item:
                                for list_item in item["items"]:
                                    f.write(f"* {list_item}\n")
                                f.write("\n")
                            elif item_type == "bullet":
                                f.write(f"* {item_content}\n\n")
                            elif item_type == "image" and "url" in item:
                                caption = item.get("caption", "")
                                if caption:
                                    f.write(f"![{caption}]({item['url']})\n\n")
                                else:
                                    f.write(f"![]({item['url']})\n\n")
                            else:
                                # Default to paragraph
                                f.write(f"{item_content}\n\n")


                # Add timestamp
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n\n*Generated: {timestamp}*")

            logger.info(f"Created markdown file: {md_path}")

            # Convert to reMarkable format using RCU
            if self.use_rcu:
                success, result = convert_markdown_to_rm(
                    markdown_path=md_path,
                    title=title
                )

                if success:
                    logger.info(f"Successfully converted to reMarkable format: {result}")
                    return result
                else:
                    logger.error(f"RCU conversion failed: {result}")
                    # If RCU fails, try falling back to legacy method
                    if self.drawj2d_path and os.path.exists(self.drawj2d_path):
                        logger.info("Falling back to legacy conversion method...")
                        return self.create_rmdoc_legacy(url, qr_path, content)
            else:
                # Fall back to legacy conversion if RCU not available
                return self.create_rmdoc_legacy(url, qr_path, content)

        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
            return None

        # Automated index notebook update (non-blocking)
        if self.pdf_service is not None:
            import threading

            def update_index_notebook():
                """
                Regenerate the index notebook PDF after new content is processed.
                Runs in a background thread to avoid blocking user interactions.
                """
                try:
                    # Example: Gather all pages info for the index (customize as needed)
                    # Here, we use a single-page list for demonstration; in production,
                    # aggregate all notebook pages as required.
                    pages = [{
                        'title': content.get('title', 'Untitled Document'),
                        'summary': content.get('summary', ''),
                        'page_number': 1,
                        'device_location': None,
                        'links': content.get('cross_page_links', [])
                    }]
                    output_path = os.path.join(self.temp_dir, "index_notebook.pdf")
                    self.pdf_service.generate_index_notebook(
                        pages=pages,
                        output_path=output_path,
                        graph_title="Index Node Graph"
                    )
                    logger.info(f"Index notebook PDF updated at {output_path}")
                except Exception as e:
                    logger.error(f"Failed to update index notebook: {e}")

            threading.Thread(target=update_index_notebook, daemon=True).start()

        return None

    def create_rmdoc_from_html(
        self, url: str, qr_path: str, html_content: str, title: Optional[str] = None
    ) -> Optional[str]:
        """Create reMarkable document directly from HTML content.
        
        Uses RCU to convert HTML directly to reMarkable format.
        
        Args:
            url: Source URL for reference
            qr_path: Path to QR code image
            html_content: Raw HTML content
            title: Optional document title
            
        Returns:
            Path to generated .rm file or None if failed
        """
        if not self.use_rcu:
            logger.warning("RCU not available, cannot convert HTML directly")
            return None
            
        try:
            # Generate temp HTML file
            with tempfile.NamedTemporaryFile(
                suffix=".html", dir=self.temp_dir, delete=False
            ) as temp_file:
                temp_html_path = temp_file.name
                temp_file.write(html_content.encode("utf-8"))
            
            # Convert HTML to reMarkable format
            success, result = convert_html_to_rm(
                html_path=temp_html_path,
                title=title or f"Page from {url}"
            )
            
            # Clean up temp file
            try:
                os.unlink(temp_html_path)
            except OSError:
                pass
                
            if success:
                logger.info(f"Successfully converted HTML to reMarkable format: {result}")
                return result
            else:
                logger.error(f"HTML conversion failed: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error converting HTML to document: {str(e)}")
            return None

    def create_pdf_rmdoc(
        self, pdf_path: str, title: str, qr_path: Optional[str] = None
    ) -> Optional[str]:
        """Create reMarkable document from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            title: Document title
            qr_path: Optional path to QR code image
            
        Returns:
            Path to generated .rm file or None if failed
        """
        if not self.use_rcu:
            logger.warning("RCU not available, cannot convert PDF directly")
            return None
            
        try:
            # Create RCU command
            timestamp = int(time.time())
            output_path = os.path.join(
                self.temp_dir, f"pdf_{hash(pdf_path)}_{timestamp}.rm"
            )
            
            # Use RCU to convert PDF to reMarkable format
            cmd = [
                "rcu", "convert",
                "--input", pdf_path,
                "--output", output_path,
                "--title", title
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Successfully converted PDF to reMarkable format: {output_path}")
                return output_path
            else:
                logger.error(f"PDF conversion failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error converting PDF to document: {str(e)}")
            return None

    # Legacy conversion method using HCL and drawj2d (for fallback)
    def create_rmdoc_legacy(
        self, url: str, qr_path: str, content: Dict[str, Any]
    ) -> Optional[str]:
        """Legacy method to create reMarkable document using HCL and drawj2d.
        
        This is kept for compatibility when RCU is not available.
        
        Args:
            url: Source URL
            qr_path: Path to QR code image
            content: Structured content dictionary
            
        Returns:
            Path to generated .rm file or None if failed
        """
        try:
            # Ensure drawj2d is available
            if not self.drawj2d_path or not os.path.exists(self.drawj2d_path):
                logger.error("drawj2d path not available for legacy conversion")
                return None
                
            # Create HCL file
            hcl_path = self.create_hcl(url, qr_path, content)
            if not hcl_path:
                logger.error("Failed to create HCL script")
                return None
                
            # Convert to .rm file
            timestamp = int(time.time())
            rm_filename = f"rm_{hash(url)}_{timestamp}.rm"
            rm_path = os.path.join(self.temp_dir, rm_filename)
            
            # Run drawj2d
            cmd = [self.drawj2d_path, "-Trm", "-rmv6", "-o", rm_path, hcl_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0 and os.path.exists(rm_path):
                logger.info(f"Legacy conversion successful: {rm_path}")
                return rm_path
            else:
                logger.error(f"Legacy conversion failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error in legacy document creation: {str(e)}")
            return None

    # Legacy HCL creation method (for fallback)
    def create_hcl(
        self, url: str, qr_path: str, content: Dict[str, Any]
    ) -> Optional[str]:
        """Create HCL script from structured content (legacy method).
        
        Args:
            url: Source URL
            qr_path: Path to QR code image
            content: Structured content dictionary
            
        Returns:
            Path to generated HCL file or None if failed
        """
        try:
            # Implementation details of HCL generation remain the same
            # (This is the original implementation from the codebase)
            
            # Ensure we have valid content, even if minimal
            if not content:
                content = {"title": f"Page from {url}", "structured_content": []}

            logger.info(f"Creating HCL document for: {content.get('title', url)}")

            # Generate HCL file path
            hcl_filename = f"doc_{hash(url)}_{int(time.time())}.hcl"
            hcl_path = os.path.join(self.temp_dir, hcl_filename)

            # Get page dimensions from config
            page_width = CONFIG.get("PAGE_WIDTH", 2160)
            page_height = CONFIG.get("PAGE_HEIGHT", 1620)
            margin = CONFIG.get("PAGE_MARGIN", 120)
            line_height = 40

            # Get fonts from config
            heading_font = CONFIG.get("HEADING_FONT", "Liberation Sans")
            body_font = CONFIG.get("BODY_FONT", "Liberation Sans")
            code_font = CONFIG.get("CODE_FONT", "DejaVu Sans Mono")

            with open(hcl_path, "w", encoding="utf-8") as f:
                # Set page size - use direct syntax based on drawj2d docs
                f.write(f'puts "size {page_width} {page_height}"\n\n')

                # Set font and pen
                f.write(f'puts "set_font {heading_font} 36"\n')
                f.write('puts "pen black"\n\n')

                # Set title position
                y_pos = margin

                # Add title
                title = content.get("title", "Untitled Document")
                f.write(
                    f'puts "text {margin} {y_pos} \\"{self._escape_hcl(title)}\\""\n'
                )
                # Space after title
                y_pos += line_height

                # Add URL under title
                f.write(f'puts "set_font {body_font} 20"\n')
                f.write(
                    f'puts "text {margin} {y_pos} \\"Source: {self._escape_hcl(url)}\\""\n'
                )
                y_pos += line_height

                # Add horizontal line separator
                f.write(
                    f'puts "line {margin} {y_pos} {page_width - margin} {y_pos} width=1.0"\n'
                )
                y_pos += line_height

                # Add QR code if available
                if qr_path and os.path.exists(qr_path):
                    qr_size = 350
                    qr_x = page_width - margin - qr_size
                    f.write(
                        f'puts "rectangle {qr_x-5} {y_pos-5} {qr_size+10} {qr_size+10} width=1.0"\n'
                    )
                    f.write(
                        f'puts "image {qr_x} {y_pos} {qr_size} {qr_size} \\"{qr_path}\\""\n'
                    )
                    # Move y_pos past the QR code
                    y_pos += qr_size + self.line_height

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
                                f'puts "text {margin + 20} {y_pos} \\"- {self._escape_hcl(sub_item_content)}\\""\n'
                            )
                            y_pos += line_height
                    else:
                        item_content = item.get("content", "")
                        if not item_content:
                            continue

                    # Check if we need a new page
                    if y_pos > (page_height - margin * 2):
                        f.write('puts "newpage"\n')
                        y_pos = margin

                    # Process based on content type
                    if item_type == "h1" or item_type == "heading":
                        f.write(f'puts "set_font {heading_font} 32"\n')
                        f.write(
                            f'puts "text {margin} {y_pos} \\"{self._escape_hcl(item_content)}\\""\n'
                        )
                        f.write(f'puts "set_font {body_font} 20"\n')
                        y_pos += line_height * 1.5
                    elif item_type == "h2":
                        f.write(f'puts "set_font {heading_font} 28"\n')
                        f.write(
                            f'puts "text {margin} {y_pos} \\"{self._escape_hcl(item_content)}\\""\n'
                        )
                        f.write(f'puts "set_font {body_font} 20"\n')
                        y_pos += line_height * 1.3
                    elif item_type == "h3" or item_type in ["h4", "h5", "h6"]:
                        f.write(f'puts "set_font {heading_font} 24"\n')
                        f.write(
                            f'puts "text {margin} {y_pos} \\"{self._escape_hcl(item_content)}\\""\n'
                        )
                        f.write(f'puts "set_font {body_font} 20"\n')
                        y_pos += line_height * 1.2
                    elif item_type == "code":
                        # Start code block
                        code_x = margin + 20
                        code_y = y_pos + line_height
                        code_lines = item_content.split("\n")
                        code_height = (
                            len(code_lines) * line_height + line_height
                        )

                        # Draw code block background and border
                        f.write(
                            f'puts "rectangle {margin} {y_pos} {page_width - margin*2} {code_height} width=1.0"\n'
                        )

                        # Process each line of code
                        f.write(f'puts "set_font {code_font} 18"\n')
                        for i, line in enumerate(code_lines):
                            line_y = code_y + (i * line_height)
                            f.write(
                                f'puts "text {code_x} {line_y} \\"{self._escape_hcl(line)}\\""\n'
                            )

                        f.write(f'puts "set_font {body_font} 20"\n')
                        y_pos += code_height + line_height
                    elif item_type == "list" or item_type == "bullet":
                        list_indent = 30

                        if item_type == "list" and "items" in item:
                            # Handle old-style list format
                            for list_item in item["items"]:
                                f.write(f'puts "text {margin} {y_pos} \\"• \\"\n')
                                f.write(
                                    f'puts "text {margin + list_indent} {y_pos} \\"{self._escape_hcl(list_item)}\\""\n'
                                )
                                y_pos += line_height
                        else:
                            # Handle single bullet point
                            f.write(f'puts "text {margin} {y_pos} \\"• \\"\n')
                            f.write(
                                f'puts "text {margin + list_indent} {y_pos} \\"{self._escape_hcl(item_content)}\\""\n'
                            )
                            y_pos += line_height
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
                                    f'puts "text {margin} {y_pos} \\"{self._escape_hcl(current_line)}\\""\n'
                                )
                                y_pos += line_height
                                current_line = word

                        # Write the last line if not empty
                        if current_line:
                            f.write(
                                f'puts "text {margin} {y_pos} \\"{self._escape_hcl(current_line)}\\""\n'
                            )
                            y_pos += line_height

                    # Add spacing between items
                    y_pos += line_height * 0.5

                # Add timestamp at the bottom of the last page
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(
                    f'puts "text {margin} {page_height - margin} \\"Generated: {timestamp}\\""\n'
                )

            logger.info(f"Created HCL file: {hcl_path}")
            return hcl_path
            
        except Exception as e:
            logger.error(f"Error creating HCL document: {e}")
            return None

<<<<<<< HEAD
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
        """Convert HCL file to Remarkable format using drawj2d with verbose logging and fallback."""
        try:
            logger.info(f"Starting conversion from {hcl_path} to {rm_path}")

            # Input validation
            if not os.path.exists(hcl_path):
                error_msg = format_error("input", "HCL file not found", hcl_path)
                logger.error(error_msg)
                return None

            # Read and log HCL content for debugging
            try:
                with open(hcl_path, "r", encoding="utf-8") as f:
                    hcl_content = f.read()
                    logger.debug(f"HCL file full content: {hcl_content}")
                    # Basic syntax check
                    if 'puts \"size' not in hcl_content or 'puts \"text' not in hcl_content:
                        logger.error("HCL file missing required content elements")
                        return None
            except Exception as e:
                logger.error(f"Failed to read HCL file: {e}")
                return None

            # Ensure output directory exists
            output_dir = os.path.dirname(rm_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)

            # Prepare conversion commands: use rm v6 format by default
            if not os.path.isfile(self.drawj2d_path) or not os.access(self.drawj2d_path, os.X_OK):
                logger.error(f"drawj2d executable not found or not executable at: {self.drawj2d_path}")
                return None
            # Primary: reMarkable v6 (rm) format; Fallback: standard rm format
            primary_cmd = [self.drawj2d_path, "-Trm", "-rmv6", "-o", rm_path, hcl_path]
            fallback_cmd = [self.drawj2d_path, "-Trm", "-o", rm_path, hcl_path]
            logger.info(f"Primary conversion command: {' '.join(primary_cmd)}")
            logger.info(f"Fallback conversion command: {' '.join(fallback_cmd)}")

            # Try primary command
            try:
                result = subprocess.run(primary_cmd, capture_output=True, text=True)
                logger.debug(f"Command stdout: {result.stdout}")
                logger.debug(f"Command stderr: {result.stderr}")
                if result.returncode != 0:
                    logger.warning("rmv6 format failed, trying older format")
                    result = subprocess.run(fallback_cmd, capture_output=True, text=True)
                    logger.debug(f"Fallback stdout: {result.stdout}")
                    logger.debug(f"Fallback stderr: {result.stderr}")
                    if result.returncode != 0:
                        raise RuntimeError(f"All conversion attempts failed: {result.stderr}")
            except Exception as conv_error:
                logger.error(f"Conversion error: {conv_error}")
                return None

            # Verify output file
            if not os.path.exists(rm_path):
                logger.error(f"Output file missing: {rm_path}")
                return None
            file_size = os.path.getsize(rm_path)
            logger.info(f"Output file created: {rm_path} ({file_size} bytes)")
            if file_size < 50:
                logger.error(f"Output file too small: {file_size} bytes")
                return None

            # Read and log binary header for debugging
            try:
                with open(rm_path, "rb") as rf:
                    header = rf.read(100)
                    logger.debug(f"RM file header (hex): {header.hex()}")
            except Exception as e:
                logger.warning(f"Could not read RM file header: {e}")

            return rm_path
        except Exception as e:
            logger.error(format_error("conversion", "Failed to convert document", e))
            return None

=======
>>>>>>> main
    def _escape_hcl(self, text: str) -> str:
        """Escape special characters for HCL."""
        if not text:
            return ""
        return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
