"""Concrete processors for InkLink.

This package provides concrete processors for different content types.
"""

from inklink.pipeline.processors.url_processor import URLProcessor
from inklink.pipeline.processors.qr_processor import QRProcessor
from inklink.pipeline.processors.web_content_processor import WebContentProcessor
from inklink.pipeline.processors.document_processor import DocumentProcessor
from inklink.pipeline.processors.upload_processor import UploadProcessor
from inklink.pipeline.processors.ai_processor import AIProcessor
from inklink.pipeline.processors.ingest_processor import IngestProcessor

__all__ = [
    "URLProcessor",
    "QRProcessor",
    "WebContentProcessor",
    "DocumentProcessor",
    "UploadProcessor",
    "AIProcessor",
    "IngestProcessor",
]
