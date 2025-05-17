"""Pipeline factory for InkLink.

This module provides a factory for creating pipelines for different content types.
"""

import logging
from typing import Any, Dict, Optional

from inklink.pipeline.pipeline import Pipeline
from inklink.pipeline.processors import (
    AIProcessor,
    DocumentProcessor,
    QRProcessor,
    UploadProcessor,
    URLProcessor,
    WebContentProcessor,
)
from inklink.pipeline.processors.ingest_processor import IngestProcessor

logger = logging.getLogger(__name__)


class PipelineFactory:
    """Factory for creating pipelines for different content types."""

    def __init__(self, services: Dict[str, Any]):
        """
        Initialize with services.

        Args:
            services: Dictionary of services
        """
        self.services = services

    def create_web_pipeline(self) -> Pipeline:
        """
        Create a pipeline for processing web content.

        Returns:
            Pipeline for web content
        """
        # Create processors
        url_processor = URLProcessor()
        qr_processor = QRProcessor(self.services.get("qr_service"))
        web_content_processor = WebContentProcessor(
            self.services.get("web_scraper"), self.services.get("pdf_service")
        )
        ai_processor = AIProcessor(self.services.get("ai_service"))
        document_processor = DocumentProcessor(self.services.get("document_service"))
        upload_processor = UploadProcessor(self.services.get("remarkable_service"))

        # Create and configure pipeline
        pipeline = Pipeline(name="WebPipeline")
        pipeline.add_processor(url_processor)
        pipeline.add_processor(qr_processor)
        pipeline.add_processor(web_content_processor)
        pipeline.add_processor(ai_processor)
        pipeline.add_processor(document_processor)
        pipeline.add_processor(upload_processor)

        return pipeline

    def create_pdf_pipeline(self) -> Pipeline:
        """
        Create a pipeline for processing PDF content.

        Returns:
            Pipeline for PDF content
        """
        # Create processors
        url_processor = URLProcessor()
        qr_processor = QRProcessor(self.services.get("qr_service"))
        web_content_processor = WebContentProcessor(
            self.services.get("web_scraper"), self.services.get("pdf_service")
        )
        document_processor = DocumentProcessor(self.services.get("document_service"))
        upload_processor = UploadProcessor(self.services.get("remarkable_service"))

        # Create and configure pipeline
        pipeline = Pipeline(name="PDFPipeline")
        pipeline.add_processor(url_processor)
        pipeline.add_processor(qr_processor)
        pipeline.add_processor(web_content_processor)
        pipeline.add_processor(document_processor)
        pipeline.add_processor(upload_processor)

        return pipeline

    def create_ingest_pipeline(self) -> Pipeline:
        """
        Create a pipeline for processing ingested content.

        Returns:
            Pipeline for ingested content
        """
        # Create processors
        ingest_processor = IngestProcessor()
        qr_processor = QRProcessor(self.services.get("qr_service"))
        ai_processor = AIProcessor(self.services.get("ai_service"))
        document_processor = DocumentProcessor(self.services.get("document_service"))
        upload_processor = UploadProcessor(self.services.get("remarkable_service"))

        # Create and configure pipeline
        pipeline = Pipeline(name="IngestPipeline")
        pipeline.add_processor(ingest_processor)
        pipeline.add_processor(qr_processor)
        pipeline.add_processor(ai_processor)
        pipeline.add_processor(document_processor)
        pipeline.add_processor(upload_processor)

        return pipeline

    def create_pipeline_for_url(self, url: str) -> Pipeline:
        """
        Create a pipeline for processing the given URL.

        Args:
            url: URL to process

        Returns:
            Appropriate pipeline for the URL
        """
        # Check if URL is a PDF
        if self.services.get("pdf_service").is_pdf_url(url):
            return self.create_pdf_pipeline()
        return self.create_web_pipeline()
