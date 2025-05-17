"""Markdown content converter for InkLink.

This module provides a converter that transforms structured content
into Markdown and then into reMarkable-compatible formats.
"""

import logging
import os
from typing import Any, Dict, Optional

from inklink.services.converters.base_converter import BaseConverter
from inklink.utils import convert_markdown_to_rm

logger = logging.getLogger(__name__)


class MarkdownConverter(BaseConverter):
    """Converts structured content to Markdown and then to reMarkable format."""

    def can_convert(self, content_type: str) -> bool:
        """Check if this converter can handle the given content type."""
        return content_type in ["structured", "markdown"]

    @staticmethod
    def convert(
        self, content: Dict[str, Any], output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert structured content to reMarkable format via Markdown.

        Args:
            content: Dictionary containing structured content and metadata
                    Should include:
                    - url: Source URL
                    - qr_path: Path to QR code image (optional)
                    - title: Content title
                    - structured_content or pages: The actual content
            output_path: Optional explicit output path

        Returns:
            Path to generated .rm file or None if failed
        """
        try:
            url = content.get("url", "")
            qr_path = content.get("qr_path", "")
            title = content.get("title", f"Page from {url}")

            # Generate markdown file path if not provided
            if not output_path:
                output_path = self._generate_temp_path("doc", url, "md")

            logger.info(f"Creating document for: {title}")

            # Detect enhanced format (pages/cross_page_links) or legacy (structured_content)
            pages = content.get("pages")
            cross_page_links = content.get("cross_page_links")
            if pages is None:
                # Fallback to legacy
                pages = content.get("structured_content", [])
                cross_page_links = content.get("cross_page_links", [])

            # Write markdown file
            self._write_markdown_file(
                output_path,
                url,
                qr_path,
                title,
                pages,
                cross_page_links,
                content.get("raw_markdown"),
            )

            logger.info(f"Created markdown file: {output_path}")

            # Convert to reMarkable format
            use_drawj2d = content.get("use_drawj2d", True)
            if use_drawj2d:
                success, result = convert_markdown_to_rm(
                    markdown_path=output_path, title=title
                )

                if success:
                    logger.info(
                        f"Successfully converted to reMarkable format: {result}"
                    )
                    return result
                logger.error(f"Markdown conversion failed: {result}")
                return None
            logger.error("drawj2d not available for Markdown conversion")
            return None

        except Exception as e:
            logger.error(f"Error converting markdown: {str(e)}")
            return None

    def _write_markdown_file(
        self,
        md_path: str,
        url: str,
        qr_path: str,
        title: str,
        pages: list,
        cross_page_links: list,
        raw_markdown: Optional[str] = None,
    ) -> None:
        """
        Write structured content to a Markdown file.

        Args:
            md_path: Path to output markdown file
            url: Source URL
            qr_path: Path to QR code image
            title: Document title
            pages: List of page content items
            cross_page_links: List of cross-page links
            raw_markdown: Optional raw markdown content to use instead of structured content
        """
        with open(md_path, "w", encoding="utf-8") as f:
            # Add title
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
            timestamp = self._get_timestamp()
            f.write(f"\n\n*Generated: {timestamp}*")
