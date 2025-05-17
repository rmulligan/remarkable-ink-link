"""Document processor for InkLink.

This module provides a processor for document generation.
"""

import logging
from typing import Any, Dict, Optional

from inklink.pipeline.processor import PipelineContext, Processor
from inklink.services.interfaces import IDocumentService

logger = logging.getLogger(__name__)


class DocumentProcessor(Processor):
    """Generates reMarkable documents from content."""

    def __init__(self, document_service: IDocumentService):
        """
        Initialize with document service.

        Args:
            document_service: Document service for creating reMarkable documents
        """
        self.document_service = document_service

    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process the context by generating a reMarkable document.

        Args:
            context: Pipeline context with content

        Returns:
            Updated pipeline context with document path
        """
        # Skip if no content or there are errors
        if not context.content or context.has_errors():
            return context

        try:
            # Get content type from context
            content_type = getattr(context, "content_type", "webpage")

            # Generate document based on content type
            if content_type == "pdf":
                return self._process_pdf_document(context)
            return self._process_web_document(context)

        except Exception as e:
            logger.error(f"Error generating document: {str(e)}")
            context.add_error(
                f"Failed to generate document: {str(e)}", processor=str(self)
            )

        return context

    def _process_pdf_document(self, context: PipelineContext) -> PipelineContext:
        """
        Process PDF document.

        Args:
            context: Pipeline context with PDF content

        Returns:
            Updated pipeline context with document path
        """
        pdf_path = context.get_artifact("pdf_path", "")
        title = context.get_artifact("title", "")
        qr_path = context.get_artifact("qr_path", "")

        if not pdf_path:
            context.add_error("No PDF path found", processor=str(self))
            return context

        try:
            # Create reMarkable document from PDF
            rm_path = self.document_service.create_pdf_rmdoc(pdf_path, title, qr_path)

            if not rm_path:
                context.add_error("Failed to create PDF document", processor=str(self))
                return context

            # Add document path to context
            context.add_artifact("rm_path", rm_path)
            context.add_artifact("document_title", title)

            logger.info(f"PDF document created: {title}")

        except Exception as e:
            logger.error(f"Error creating PDF document: {str(e)}")
            context.add_error(
                f"Failed to create PDF document: {str(e)}", processor=str(self)
            )

        return context

    def _process_web_document(self, context: PipelineContext) -> PipelineContext:
        """
        Process web document.

        Args:
            context: Pipeline context with web content

        Returns:
            Updated pipeline context with document path
        """
        url = context.url
        qr_path = context.get_artifact("qr_path", "")
        content = context.content

        try:
            # Create reMarkable document from content
            rm_path = self.document_service.create_rmdoc_from_content(
                url, qr_path, content
            )

            if not rm_path:
                context.add_error("Failed to create web document", processor=str(self))
                return context

            # Add document path to context
            context.add_artifact("rm_path", rm_path)
            context.add_artifact("document_title", content.get("title", url))

            logger.info(f"Web document created: {content.get('title', url)}")

        except Exception as e:
            logger.error(f"Error creating web document: {str(e)}")
            context.add_error(
                f"Failed to create web document: {str(e)}", processor=str(self)
            )

        return context
