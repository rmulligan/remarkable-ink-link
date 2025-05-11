"""Dependency injection container for InkLink.

This module provides a container for configuring and resolving dependencies.
"""

import logging
import os
from typing import Dict, Any, Optional

from inklink.di.service_provider import ServiceProvider
from inklink.services.interfaces import (
    IQRCodeService,
    IWebScraperService,
    IDocumentService,
    IPDFService,
    IRemarkableService,
    IHandwritingRecognitionService,
    IGoogleDocsService,
    IEPUBGenerator,
    IKnowledgeGraphService,
    IKnowledgeIndexService,
)
from inklink.services.qr_service import QRCodeService
from inklink.services.web_scraper_service import WebScraperService
from inklink.services.document_service import DocumentService
from inklink.services.pdf_service import PDFService
from inklink.services.remarkable_service import RemarkableService
from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)
from inklink.services.google_docs_service import GoogleDocsService
from inklink.services.ai_service import AIService

# Import new services for knowledge index notebooks
from inklink.services.epub_generator import EPUBGenerator
from inklink.services.knowledge_graph_service import KnowledgeGraphService
from inklink.services.knowledge_index_service import KnowledgeIndexService

logger = logging.getLogger(__name__)


class Container:
    """
    Dependency injection container for InkLink.

    This container configures and resolves dependencies for the application.
    It provides a simple way to create a fully configured ServiceProvider.
    """

    @staticmethod
    def create_provider(config: Dict[str, Any]) -> ServiceProvider:
        """
        Create a fully configured ServiceProvider.

        Args:
            config: Configuration dictionary

        Returns:
            Configured ServiceProvider
        """
        provider = ServiceProvider(config)

        # Normalize configuration keys to lowercase
        normalized_config = {key.lower(): value for key, value in config.items()}

        # Register configuration values as services
        provider.register_instance("config", normalized_config)

        # Populate any values directly from normalized config
        temp_dir = normalized_config.get("temp_dir")
        output_dir = normalized_config.get("output_dir")
        drawj2d_path = normalized_config.get("drawj2d_path")
        rmapi_path = normalized_config.get("rmapi_path")
        rm_folder = normalized_config.get("rm_folder")

        provider.register_instance("temp_dir", temp_dir)
        provider.register_instance("output_dir", output_dir)
        provider.register_instance("drawj2d_path", drawj2d_path)
        provider.register_instance("rmapi_path", rmapi_path)
        provider.register_instance("rm_folder", rm_folder)

        # Register core services
        provider.register(IQRCodeService, QRCodeService)
        provider.register(IWebScraperService, WebScraperService)
        provider.register(IDocumentService, DocumentService)
        provider.register(IPDFService, PDFService)
        provider.register(IRemarkableService, RemarkableService)
        provider.register(IHandwritingRecognitionService, HandwritingRecognitionService)
        provider.register(IGoogleDocsService, GoogleDocsService)

        # Register services that don't have interfaces yet
        provider.register_factory(AIService, lambda: AIService())

        # Register EPUB generator service
        provider.register_factory(
            IEPUBGenerator,
            lambda: EPUBGenerator(
                output_dir=output_dir or os.path.join(temp_dir, "epub")
            ),
        )

        # Register Knowledge Graph service
        # Get Neo4j configuration from environment or config
        neo4j_uri = normalized_config.get("neo4j_uri", "bolt://localhost:7687")
        neo4j_user = normalized_config.get("neo4j_user", "neo4j")
        neo4j_pass = normalized_config.get("neo4j_pass", "password")
        neo4j_db = normalized_config.get("neo4j_db", "neo4j")

        provider.register_factory(
            IKnowledgeGraphService,
            lambda: KnowledgeGraphService(
                uri=neo4j_uri,
                username=neo4j_user,
                password=neo4j_pass,
                database=neo4j_db,
            ),
        )

        # Register Knowledge Index Service
        provider.register(IKnowledgeIndexService, KnowledgeIndexService)

        return provider
