"""
EPUB Generator Service for InkLink.

This service provides functionality to generate EPUB documents from markdown content,
enhanced with hyperlinks for navigation between related content.
"""

import logging
import os
import re
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from ebooklib import epub
from markdown import markdown

from inklink.utils.common import sanitize_filename

logger = logging.getLogger(__name__)


class EPUBGenerator:
    """
    Service for generating EPUB documents with hyperlinks.

    This service handles the conversion of markdown content to EPUB format,
    optimized for reMarkable tablets, with enhanced navigation through hyperlinks.
    """

    def __init__(self, output_dir: str = None):
        """
        Initialize the EPUB generator.

        Args:
            output_dir: Directory to save generated EPUB files (optional)
        """
        self.output_dir = output_dir or tempfile.gettempdir()
        os.makedirs(self.output_dir, exist_ok=True)

    def create_epub_from_markdown(
        self,
        title: str,
        content: str,
        author: str = "InkLink",
        entity_links: Dict[str, str] = None,
        metadata: Dict[str, Any] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create an EPUB document from markdown content.

        Args:
            title: Title of the EPUB document
            content: Markdown content
            author: Author of the document
            entity_links: Dictionary mapping entity names to their anchor IDs
            metadata: Additional metadata for the EPUB

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            # Create a new EPUB book
            book = epub.EpubBook()

            # Set metadata
            book.set_title(title)
            book.set_language("en")
            book.add_author(author)

            # Add additional metadata if provided
            if metadata:
                for key, value in metadata.items():
                    book.add_metadata("DC", key, value)

            # Enhance markdown with hyperlinks if entity_links provided
            if entity_links:
                content = self.enhance_markdown_with_hyperlinks(content, entity_links)

            # Convert markdown to HTML
            html_content = markdown(
                content, extensions=["tables", "fenced_code", "nl2br", "toc"]
            )

            # Create chapter
            chapter = epub.EpubHtml(title=title, file_name="content.xhtml")
            chapter.content = self._wrap_html_content(html_content, title)

            # Add chapter to book
            book.add_item(chapter)

            # Add navigation files
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            # Create spine
            book.spine = ["nav", chapter]

            # Determine output file path
            safe_title = sanitize_filename(title)
            output_path = os.path.join(self.output_dir, f"{safe_title}.epub")

            # Write EPUB file
            epub.write_epub(output_path, book, {})

            logger.info(f"Created EPUB file at {output_path}")

            return True, {
                "path": output_path,
                "title": title,
                "size": os.path.getsize(output_path),
            }

        except Exception as e:
            logger.error(f"Error creating EPUB: {str(e)}")
            return False, {"error": str(e)}

    @staticmethod
    def enhance_markdown_with_hyperlinks(
        markdown_content: str, entity_links: Dict[str, str]
    ) -> str:
        """
        Enhance markdown content with hyperlinks.

        Args:
            markdown_content: Original markdown content
            entity_links: Dictionary mapping entity names to their anchor IDs

        Returns:
            Enhanced markdown content with hyperlinks
        """
        # Split content into lines to process each line separately
        lines = markdown_content.splitlines()
        enhanced_lines = []

        # Sort entities by length (longest first) to avoid substring replacement issues
        sorted_entities = sorted(entity_links.keys(), key=len, reverse=True)

        # Process each line
        for line in lines:
            # Skip headings (lines starting with # characters)
            if re.match(r"^#{1,6}\s+", line):
                enhanced_lines.append(line)
                continue

            # Process normal content lines
            current_line = line
            for entity in sorted_entities:
                # Escape entity name for regex
                escaped_entity = re.escape(entity)

                # Match entity only if not already part of a link
                # Don't match if preceded by [
                # Don't match if inside a markdown link [...]
                pattern = rf"(?<!\[)\b{escaped_entity}\b(?![^\[]*\])"

                # Create link to the entity
                target = f"[{entity}](#{entity_links[entity]})"

                # Replace all occurrences in this line
                current_line = re.sub(pattern, target, current_line)

            enhanced_lines.append(current_line)

        # Join the enhanced lines back into a single string
        return "\n".join(enhanced_lines)

    @staticmethod
    def _wrap_html_content(html_content: str, title: str) -> str:
        """
        Wrap HTML content with proper tags and CSS for better reMarkable display.

        Args:
            html_content: HTML content to wrap
            title: Document title

        Returns:
            Wrapped HTML content
        """
        # Add CSS optimized for reMarkable
        css = """
        <style>
            body {
                font-family: sans-serif;
                line-height: 1.5;
                margin: 2rem;
                font-size: 1rem;
            }
            h1 { font-size: 1.8rem; margin-top: 2rem; }
            h2 { font-size: 1.5rem; margin-top: 1.5rem; }
            h3 { font-size: 1.2rem; margin-top: 1.2rem; }
            a { text-decoration: underline; color: #333; }
            code { font-family: monospace; background-color: #f0f0f0; padding: 0.1rem 0.3rem; }
            pre { background-color: #f0f0f0; padding: 1rem; overflow-x: auto; }
            table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
            th, td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; }
            th { background-color: #f0f0f0; }
        </style>
        """

        # Wrap content
        wrapped_content = f"""<!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            {css}
        </head>
        <body>
            <h1>{title}</h1>
            {html_content}
        </body>
        </html>
        """

        return wrapped_content

    @staticmethod
    def create_toc_for_entities(entities: List[Dict[str, Any]]) -> str:
        """
        Create a table of contents markdown for entity links.

        Args:
            entities: List of entity dictionaries with name, type, and references

        Returns:
            Markdown formatted table of contents
        """
        toc = "# Entity Index\n\n"

        # Group entities by type
        entities_by_type = {}
        for entity in entities:
            entity_type = entity.get("type", "Other")
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)

        # Add entity types as sections
        for entity_type, type_entities in sorted(entities_by_type.items()):
            # Add section header
            toc += f"## {entity_type}s\n\n"

            # Add entities
            for entity in sorted(type_entities, key=lambda e: e.get("name", "")):
                name = entity.get("name", "")
                ref_count = len(entity.get("references", []))

                # Create anchor ID for linking
                anchor_id = re.sub(r"[^a-zA-Z0-9]", "-", name.lower())

                # Add entity with reference count
                toc += f"- [{name}](#{anchor_id}) ({ref_count} references)\n"

            toc += "\n"

        return toc
