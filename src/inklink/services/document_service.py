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
import subprocess
from typing import Dict, Any, Optional, List

# Import utility functions for error handling and RCU integration
from inklink.utils import (
    retry_operation,
    format_error,
    ensure_rcu_available,
    convert_markdown_to_rm,
    convert_html_to_rm,
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

    def __init__(
        self, temp_dir: str, drawj2d_path: Optional[str] = None, pdf_service=None
    ):
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
        self.is_remarkable_pro = rm_model == "pro"
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
                                f.write(
                                    f"- {ref_label} (to page {ref_to}, type: {ref_type})\n"
                                )
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
                            label = link.get(
                                "label", f"Link from page {from_page} to {to_page}"
                            )
                            link_type = link.get("type", "")
                            f.write(
                                f"- {label} (from page {from_page} to page {to_page}, type: {link_type})\n"
                            )
                        f.write("\n---\n\n")

                # Add timestamp
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n\n*Generated: {timestamp}*")

            logger.info(f"Created markdown file: {md_path}")

            # Convert to reMarkable format using RCU
            if self.use_rcu:
                success, result = convert_markdown_to_rm(
                    markdown_path=md_path, title=title
                )

                if success:
                    logger.info(
                        f"Successfully converted to reMarkable format: {result}"
                    )
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
                    pages = [
                        {
                            "title": content.get("title", "Untitled Document"),
                            "summary": content.get("summary", ""),
                            "page_number": 1,
                            "device_location": None,
                            "links": content.get("cross_page_links", []),
                        }
                    ]
                    output_path = os.path.join(self.temp_dir, "index_notebook.pdf")
                    if self.pdf_service:
                        self.pdf_service.generate_index_notebook(
                            pages=pages,
                            output_path=output_path,
                            graph_title="Index Node Graph",
                        )
                    logger.info(f"Index notebook PDF updated at {output_path}")
                except Exception as e:
                    logger.error(f"Failed to update index notebook: {e}")

            threading.Thread(target=update_index_notebook, daemon=True).start()

        return None
