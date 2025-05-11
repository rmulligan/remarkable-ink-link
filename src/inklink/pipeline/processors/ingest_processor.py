"""Ingest processor for InkLink.

This module provides a processor for handling ingested content.
"""

import logging
from typing import Dict, Any, Optional, List

from inklink.pipeline.processor import Processor, PipelineContext

logger = logging.getLogger(__name__)


class IngestProcessor(Processor):
    """Processes ingested content from various sources."""

    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process the context by structuring ingested content.

        Args:
            context: Pipeline context with raw content

        Returns:
            Updated pipeline context with structured content
        """
        # Skip if no content or there are errors
        if not context.content or context.has_errors():
            return context

        try:
            # Extract content parameters
            content_type = context.content.get("type")
            title = context.content.get("title")
            content = context.content.get("content")
            metadata = context.content.get("metadata", {})

            # Validate required fields
            if not content_type or not title or not content:
                context.add_error(
                    "Missing required fields for ingestion", processor=str(self)
                )
                return context

            # Process content based on type
            structured_content = self._process_content_by_type(content_type, content)

            # Create content package
            content_package = {
                "title": title,
                "structured_content": structured_content,
                "images": [],
            }

            # Update context
            context.content = content_package
            context.add_artifact("title", title)
            context.source_url = metadata.get("source_url", "")
            context.process_with_ai = metadata.get("process_with_ai", False)
            context.upload_to_remarkable = metadata.get("upload_to_remarkable", True)

            logger.info(f"Content ingested: {title}")

        except Exception as e:
            logger.error(f"Error processing ingested content: {str(e)}")
            context.add_error(
                f"Failed to process ingested content: {str(e)}", processor=str(self)
            )

        return context

    def _process_content_by_type(
        self, content_type: str, content: Any
    ) -> List[Dict[str, Any]]:
        """
        Process content based on its type.

        Args:
            content_type: Type of content
            content: Content to process

        Returns:
            Structured content
        """
        structured_content = []

        if content_type == "web":
            # For web content, use as-is if already structured
            if isinstance(content, list):
                structured_content = content
            else:
                # Default to a single paragraph if content is a string
                structured_content = [{"type": "paragraph", "content": content}]

        elif content_type == "note":
            # For plain text notes, convert to paragraphs
            paragraphs = content.split("\n\n")
            structured_content = [
                {"type": "paragraph", "content": p.strip()}
                for p in paragraphs
                if p.strip()
            ]

        elif content_type == "shortcut":
            # For Siri shortcuts, handle markdown conversion if needed
            if content.startswith("#"):
                # Simple markdown parsing
                lines = content.split("\n")
                current_item = None

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    if line.startswith("# "):
                        structured_content.append({"type": "h1", "content": line[2:]})
                    elif line.startswith("## "):
                        structured_content.append({"type": "h2", "content": line[3:]})
                    elif line.startswith("### "):
                        structured_content.append({"type": "h3", "content": line[4:]})
                    elif line.startswith("- ") or line.startswith("* "):
                        if current_item and current_item["type"] == "list":
                            current_item["items"].append(line[2:])
                        else:
                            current_item = {"type": "list", "items": [line[2:]]}
                            structured_content.append(current_item)
                    else:
                        structured_content.append(
                            {"type": "paragraph", "content": line}
                        )
            else:
                structured_content = [{"type": "paragraph", "content": content}]
        else:
            # Default handling for unknown content types
            structured_content = [{"type": "paragraph", "content": content}]

        return structured_content
