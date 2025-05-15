"""Dependency injection container for InkLink.

This module provides a container for configuring and resolving dependencies.
"""

import logging
import os
from typing import Any, Dict, Optional

from inklink.adapters.claude_vision_adapter import ClaudeVisionAdapter

# Import adapters
from inklink.adapters.handwriting_adapter import HandwritingAdapter

# Import Limitless services
from inklink.adapters.limitless_adapter import LimitlessAdapter
from inklink.di.service_provider import ServiceProvider
from inklink.services.ai_service import AIService
from inklink.services.document_service import DocumentService

# Import new services for knowledge index notebooks
from inklink.services.epub_generator import EPUBGenerator
from inklink.services.google_docs_service import GoogleDocsService
from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)
from inklink.services.interfaces import (
    IDocumentService,
    IEPUBGenerator,
    IGoogleDocsService,
    IHandwritingRecognitionService,
    IKnowledgeGraphService,
    IKnowledgeIndexService,
    ILimitlessLifeLogService,
    IPDFService,
    IQRCodeService,
    IRemarkableService,
    IWebScraperService,
)
from inklink.services.knowledge_graph_integration_service import (
    KnowledgeGraphIntegrationService,
)
from inklink.services.knowledge_graph_service import KnowledgeGraphService
from inklink.services.knowledge_index_service import KnowledgeIndexService
from inklink.services.limitless_life_log_service import LimitlessLifeLogService
from inklink.services.limitless_scheduler_service import LimitlessSchedulerService
from inklink.services.pdf_service import PDFService
from inklink.services.qr_service import QRCodeService
from inklink.services.remarkable_service import RemarkableService
from inklink.services.web_scraper_service import WebScraperService

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

        # Set up Handwriting Recognition with Claude CLI
        claude_command = normalized_config.get("claude_command", "claude")
        claude_model = normalized_config.get("claude_model", "")

        # Create and register Claude Vision adapter
        claude_vision_adapter = ClaudeVisionAdapter(
            claude_command=claude_command, model=claude_model
        )

        # Create and register Handwriting adapter
        handwriting_adapter = HandwritingAdapter(
            claude_command=claude_command, model=claude_model
        )

        # Create and register Handwriting recognition service
        handwriting_recognition_service = HandwritingRecognitionService(
            claude_command=claude_command,
            model=claude_model,
            handwriting_adapter=handwriting_adapter,
        )

        # Register services and adapters
        provider.register_instance(ClaudeVisionAdapter, claude_vision_adapter)
        provider.register_instance(HandwritingAdapter, handwriting_adapter)
        provider.register_instance(
            IHandwritingRecognitionService, handwriting_recognition_service
        )
        provider.register_instance(
            HandwritingRecognitionService, handwriting_recognition_service
        )

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

        # Get Neo4j configuration from environment or config
        neo4j_uri = normalized_config.get("neo4j_uri", "bolt://localhost:7687")
        neo4j_user = normalized_config.get("neo4j_user", "neo4j")
        neo4j_pass = normalized_config.get("neo4j_pass", "password")

        # Create knowledge graph service
        knowledge_graph_service = KnowledgeGraphService(
            uri=neo4j_uri,
            username=neo4j_user,
            password=neo4j_pass,
        )

        # Register KnowledgeGraphService
        provider.register_factory(
            IKnowledgeGraphService, lambda: knowledge_graph_service
        )
        provider.register_factory(
            KnowledgeGraphService, lambda: knowledge_graph_service
        )

        # Create and register knowledge graph integration service
        knowledge_graph_integration_service = KnowledgeGraphIntegrationService(
            handwriting_service=handwriting_recognition_service,
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

        # Register Knowledge Index Service
        provider.register(IKnowledgeIndexService, KnowledgeIndexService)

        # Create Limitless services if API key is available
        limitless_api_key = normalized_config.get("limitless_api_key")
        if limitless_api_key:
            # Create Limitless adapter
            limitless_adapter = LimitlessAdapter(
                api_key=limitless_api_key,
                base_url=normalized_config.get(
                    "limitless_api_url", "https://api.limitless.ai"
                ),
            )

            # Create Limitless Life Log service
            limitless_service = LimitlessLifeLogService(
                limitless_adapter=limitless_adapter,
                knowledge_graph_service=knowledge_graph_service,
                sync_interval=int(
                    normalized_config.get("limitless_sync_interval", 3600)
                ),
                storage_path=normalized_config.get(
                    "limitless_storage_path", os.path.join(temp_dir, "limitless")
                ),
            )

            # Create Limitless scheduler service
            limitless_scheduler = LimitlessSchedulerService(
                limitless_service=limitless_service,
                sync_interval=int(
                    normalized_config.get("limitless_sync_interval", 3600)
                ),
            )

            # Register Limitless services
            provider.register_factory(
                ILimitlessLifeLogService, lambda: limitless_service
            )
            provider.register_factory(
                LimitlessLifeLogService, lambda: limitless_service
            )
            provider.register_factory(
                LimitlessSchedulerService, lambda: limitless_scheduler
            )

            # Register service instances
            provider.register_instance("limitless_adapter", limitless_adapter)
            provider.register_instance("limitless_service", limitless_service)
            provider.register_instance("limitless_scheduler", limitless_scheduler)

            # Start the scheduler if auto-start is enabled
            if normalized_config.get("limitless_autostart", "true").lower() == "true":
                limitless_scheduler.start()
                logger.info("Limitless scheduler autostarted")
        else:
            logger.info("Limitless integration disabled (no API key provided)")

        return provider
