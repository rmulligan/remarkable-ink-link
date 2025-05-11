"""Service for generating EPUB documents with hyperlinks for reMarkable."""

import logging
import os
import tempfile
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple

from ebooklib import epub
import html
import markdown

logger = logging.getLogger(__name__)


class EPUBGenerator:
    """
    Service for generating EPUB documents with hyperlinks for reMarkable.

    This service creates EPUB files from markdown content, preserving hyperlinks
    and adding navigation features for better reading experience on reMarkable.
    """

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the EPUB generator.

        Args:
            output_dir: Directory for output files (defaults to system temp dir)
        """
        self.output_dir = output_dir or tempfile.gettempdir()
        os.makedirs(self.output_dir, exist_ok=True)

    def create_epub_from_markdown(
        self,
        markdown_content: str,
        title: str,
        author: str = "InkLink",
        language: str = "en",
        filename: Optional[str] = None,
    ) -> str:
        """
        Create an EPUB file from markdown content.

        Args:
            markdown_content: Markdown content to convert
            title: Title of the EPUB
            author: Author name
            language: Language code
            filename: Optional filename (generated if not provided)

        Returns:
            Path to the generated EPUB file
        """
        try:
            # Create a new EPUB book
            book = epub.EpubBook()

            # Set metadata
            book.set_identifier(str(uuid.uuid4()))
            book.set_title(title)
            book.set_language(language)
            book.add_author(author)

            # Process markdown sections
            chapters = self._process_markdown_to_chapters(markdown_content, title)

            # Add chapters to the book
            for chapter in chapters:
                book.add_item(chapter)

            # Create table of contents
            toc = []
            nav_items = []

            for i, chapter in enumerate(chapters):
                # Add to table of contents
                toc.append(epub.Link(chapter.file_name, chapter.title, f"chapter_{i}"))
                nav_items.append(chapter)

            # Add navigation files
            book.toc = toc
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            # Create spine
            book.spine = ["nav"] + nav_items

            # Generate filename if not provided
            if not filename:
                filename = (
                    f"{title.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}.epub"
                )

            # Ensure filename has .epub extension
            if not filename.endswith(".epub"):
                filename += ".epub"

            # Generate full output path
            output_path = os.path.join(self.output_dir, filename)

            # Write the EPUB file
            epub.write_epub(output_path, book, {})

            logger.info(f"Created EPUB file: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error creating EPUB: {e}")
            return ""

    def _process_markdown_to_chapters(
        self, markdown_content: str, book_title: str
    ) -> List[epub.EpubHtml]:
        """
        Process markdown content into chapters.

        Args:
            markdown_content: Markdown content to process
            book_title: Title of the book

        Returns:
            List of EPUB chapters
        """
        # Split markdown by H1 (# ) headings
        chapter_sections = re.split(r"\n# ", markdown_content)

        # If there's text before the first heading, add it as an introduction
        if not chapter_sections[0].startswith("# "):
            intro_text = chapter_sections[0]
            chapter_sections = chapter_sections[1:]
        else:
            intro_text = ""

        # Create a list to hold all chapters
        chapters = []

        # Create an introduction/cover chapter
        cover = epub.EpubHtml(title=book_title, file_name="cover.xhtml", lang="en")
        cover.content = f"<h1>{html.escape(book_title)}</h1>"

        if intro_text:
            # Convert markdown to HTML
            intro_html = markdown.markdown(intro_text, extensions=["extra", "tables"])
            cover.content += intro_html

        chapters.append(cover)

        # Process each chapter section
        for i, section in enumerate(chapter_sections):
            # Reconstruct the heading that was removed by the split
            section_content = f"# {section}" if i > 0 else section

            # Extract the chapter title from the first heading
            title_match = re.match(r"# (.*?)\n", section_content)
            if title_match:
                chapter_title = title_match.group(1)
            else:
                chapter_title = f"Chapter {i + 1}"

            # Create chapter
            chapter = epub.EpubHtml(
                title=chapter_title, file_name=f"chapter_{i + 1}.xhtml", lang="en"
            )

            # Convert markdown to HTML
            html_content = markdown.markdown(
                section_content, extensions=["extra", "tables"]
            )

            # Add CSS class for styling
            html_content = html_content.replace("<table>", '<table class="data-table">')

            # Create enhanced HTML with CSS
            chapter.content = f"""
            <html>
            <head>
                <title>{html.escape(chapter_title)}</title>
                <style>
                    body {{
                        font-family: serif;
                        margin: 0.5em;
                        padding: 0.5em;
                    }}
                    h1, h2, h3 {{ margin-top: 1em; }}
                    .data-table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 1em 0;
                    }}
                    .data-table td, .data-table th {{
                        border: 1px solid #ddd;
                        padding: 0.4em;
                    }}
                    a {{ color: #0000EE; text-decoration: underline; }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

            chapters.append(chapter)

        return chapters

    def enhance_markdown_with_hyperlinks(
        self, markdown_content: str, entity_links: Dict[str, str]
    ) -> str:
        """
        Enhance markdown content with hyperlinks.

        Args:
            markdown_content: Original markdown content
            entity_links: Dictionary mapping entity names to anchors

        Returns:
            Enhanced markdown with hyperlinks
        """
        enhanced_content = markdown_content

        # Create regex pattern for entity names, matching whole words only
        # Sort entity names by length (longest first) to avoid partial replacements
        sorted_entities = sorted(entity_links.keys(), key=len, reverse=True)

        for entity in sorted_entities:
            # Escape regex special characters in the entity name
            escaped_entity = re.escape(entity)
            # Replace occurrences with links, but not in headings or if already in links
            pattern = rf"(?<![#\[])\b{escaped_entity}\b(?![^\[]*\])"
            target = f"[{entity}](#{entity_links[entity]})"
            enhanced_content = re.sub(pattern, target, enhanced_content)

        return enhanced_content
