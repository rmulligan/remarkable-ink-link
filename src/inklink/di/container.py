"""Dependency injection container for InkLink.

This module provides a container for configuring and resolving dependencies.
"""

import logging
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
from inklink.services.knowledge_graph_service import KnowledgeGraphService
from inklink.services.knowledge_graph_integration_service import (
    KnowledgeGraphIntegrationService,
)

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

        # Register services
        provider.register(IQRCodeService, QRCodeService)
        provider.register(IWebScraperService, WebScraperService)
        provider.register(IDocumentService, DocumentService)
        provider.register(IPDFService, PDFService)
        provider.register(IRemarkableService, RemarkableService)
        provider.register(IHandwritingRecognitionService, HandwritingRecognitionService)
        provider.register(IGoogleDocsService, GoogleDocsService)

        # Register services that don't have interfaces yet
        provider.register_factory(AIService, lambda: AIService())

        # Register knowledge graph services
        knowledge_graph_service = KnowledgeGraphService()
        provider.register_factory(
            KnowledgeGraphService, lambda: knowledge_graph_service
        )

        # Create and register knowledge graph integration service
        handwriting_service = provider.resolve(IHandwritingRecognitionService)
        knowledge_graph_integration_service = KnowledgeGraphIntegrationService(
            handwriting_service=handwriting_service,
            knowledge_graph_service=knowledge_graph_service,
        )
        provider.register_factory(
            KnowledgeGraphIntegrationService,
            lambda: knowledge_graph_integration_service,
        )

        # Register service instances for direct access
        provider.register_instance("knowledge_graph_service", knowledge_graph_service)
        provider.register_instance(
            "knowledge_graph_integration_service", knowledge_graph_integration_service
        )

        # Normalize configuration keys to lowercase
        normalized_config = {key.lower(): value for key, value in config.items()}

        # Register configuration values as services
        provider.register_instance("config", normalized_config)

        # Populate any values directly from normalized config
        provider.register_instance("temp_dir", normalized_config.get("temp_dir"))
        provider.register_instance("output_dir", normalized_config.get("output_dir"))
        provider.register_instance(
            "drawj2d_path", normalized_config.get("drawj2d_path")
        )
        provider.register_instance("rmapi_path", normalized_config.get("rmapi_path"))
        provider.register_instance("rm_folder", normalized_config.get("rm_folder"))

        return provider
