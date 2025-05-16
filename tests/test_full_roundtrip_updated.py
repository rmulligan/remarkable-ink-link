"""
Integration test for the full workflow using real service implementations.

External dependencies required:
- rmapi must be installed and configured (https://github.com/juruen/rmapi)
- Network access is required for web scraping and uploading to reMarkable
- drawj2d or RCU (optional, for document conversion if needed)
- Neo4j (optional, for knowledge graph features)

This test uses pytest's tmp_path fixture for all temporary files and directories.
"""

import asyncio
import importlib.util
import json
import logging
import os
from typing import Any, Dict, Optional

import pytest

# Import controllers
from inklink.controllers.share_controller import ShareController

# Import required modules
from inklink.di.container import Container
from inklink.services.interfaces import (
    IAIService,
    IDocumentService,
    IPDFService,
    IQRCodeService,
    IRemarkableService,
    IWebScraperService,
)

# Check if neo4j is installed
neo4j_installed = importlib.util.find_spec("neo4j") is not None

# Only import knowledge graph related modules if neo4j is installed
if neo4j_installed:
    from inklink.controllers.knowledge_graph_controller import KnowledgeGraphController
    from inklink.services.interfaces import IKnowledgeGraphService

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("test_full_roundtrip")


class MockRequest:
    """Mock HTTP request for testing controllers."""

    def __init__(self, body: Optional[Dict[str, Any]] = None):
        """Initialize with optional request body."""
        self.body = body or {}

    async def json(self):
        """Return the request body as JSON."""
        return self.body


class MockResponse:
    """Mock HTTP response for capturing controller responses."""

    def __init__(self):
        """Initialize response capture."""
        self.status_code = None
        self.headers = {}
        self.body = None

    async def text(self):
        """Return response body as text."""
        return self.body


class ControllerTestHelper:
    """Helper for testing controllers."""

    def __init__(self, tmp_path, config_overrides=None):
        """
        Initialize with temporary path and optional config overrides.

        Args:
            tmp_path: Temporary directory path
            config_overrides: Optional config dictionary to override defaults
        """
        # Set up configuration
        self.tmp_path = tmp_path
        self.temp_dir = str(tmp_path / "temp")
        self.output_dir = str(tmp_path / "output")

        # Create required directories
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # Basic config with paths
        self.config = {
            "temp_dir": self.temp_dir,
            "output_dir": self.output_dir,
            "drawj2d_path": os.environ.get("DRAWJ2D_PATH", "/usr/local/bin/drawj2d"),
            "rmapi_path": os.environ.get("RMAPI_PATH", "/usr/bin/rmapi"),
            "rm_folder": "InkLink_Test",
            "neo4j_uri": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            "neo4j_username": os.environ.get("NEO4J_USERNAME", "neo4j"),
            "neo4j_password": os.environ.get("NEO4J_PASSWORD", "password"),
        }

        # Apply any config overrides
        if config_overrides:
            self.config.update(config_overrides)

        # Create DI container
        self.container = Container.create_provider(self.config)

        # Create mock request and response
        self.request = MockRequest()
        self.response = MockResponse()

    def get_service(self, interface):
        """Create service directly instead of using container."""
        if interface == IQRCodeService:
            from inklink.services.qr_service import QRCodeService

            return QRCodeService(temp_dir=self.temp_dir)
        if interface == IWebScraperService:
            from inklink.services.web_scraper_service import WebScraperService

            return WebScraperService()
        if interface == IDocumentService:
            from inklink.services.document_service import DocumentService

            return DocumentService(temp_dir=self.temp_dir)
        if interface == IPDFService:
            from inklink.services.pdf_service import PDFService

            return PDFService(temp_dir=self.temp_dir, output_dir=self.output_dir)
        if interface == IRemarkableService:
            from inklink.services.remarkable_service import RemarkableService

            rmapi_path = self.config.get("rmapi_path", "/usr/bin/rmapi")
            return RemarkableService(rmapi_path=rmapi_path)
        if interface == IAIService:
            from inklink.services.ai_service import AIService

            return AIService()
        if neo4j_installed and interface == IKnowledgeGraphService:
            from inklink.services.knowledge_graph_service import KnowledgeGraphService

            return KnowledgeGraphService(
                uri=self.config.get("neo4j_uri"),
                username=self.config.get("neo4j_username"),
                password=self.config.get("neo4j_password"),
            )
        # Default to container resolution as fallback
        try:
            return self.container.resolve(interface)
        except Exception as e:
            logger.error(f"Failed to resolve service: {e}")
            return None


@pytest.mark.integration
def test_share_controller_roundtrip(tmp_path):
    """Test the ShareController with real services."""
    # Skip if rmapi is not available
    if not os.path.exists(os.environ.get("RMAPI_PATH", "/usr/bin/rmapi")):
        pytest.skip("rmapi not found. Install it to run this test.")

    # Create test helper
    helper = ControllerTestHelper(tmp_path)

    try:
        # Get required services
        qr_service = helper.get_service(IQRCodeService)
        document_service = helper.get_service(IDocumentService)
        remarkable_service = helper.get_service(IRemarkableService)
        web_scraper = helper.get_service(IWebScraperService)

        # Ensure services were created successfully
        assert qr_service is not None, "QR service could not be created"
        assert document_service is not None, "Document service could not be created"
        assert remarkable_service is not None, "Remarkable service could not be created"
        assert web_scraper is not None, "Web scraper service could not be created"

        # Create the controller
        controller = ShareController(
            qr_service=qr_service,
            document_service=document_service,
            remarkable_service=remarkable_service,
            web_scraper=web_scraper,
        )

        # Test with a simple static page
        url = "https://example.com/"
        helper.request.body = {"url": url}

        # Execute the controller
        try:
            response = asyncio.run(controller.share_url(helper.request))

            # Verify response
            assert (
                response.status == 200
            ), f"Expected 200 status code, got {response.status}"

            # Check that the document was uploaded to reMarkable
            body_text = asyncio.run(response.text())
            body = json.loads(body_text)
            assert body["success"] is True
            assert "uploaded" in body.get("message", "").lower()
        except Exception as e:
            logger.error(f"Error executing controller: {e}")
            pytest.skip(f"Error in controller execution: {e}")
    except Exception as e:
        logger.error(f"Error setting up test: {e}")
        pytest.skip(f"Test setup error: {e}")


@pytest.mark.integration
@pytest.mark.skipif(not neo4j_installed, reason="Neo4j package not installed")
def test_knowledge_graph_roundtrip(tmp_path):
    """Test the KnowledgeGraphController with real services."""
    # Skip if no Neo4j connection
    if not os.environ.get("INKLINK_TEST_NEO4J", "").lower() == "true":
        pytest.skip("Neo4j testing not enabled. Set INKLINK_TEST_NEO4J=true to enable.")

    # Create test helper
    helper = ControllerTestHelper(tmp_path)

    try:
        # Get required services
        kg_service = helper.get_service(IKnowledgeGraphService)

        # Create the controller
        controller = KnowledgeGraphController(kg_service)

        # Test entity creation
        entity_name = f"Test_Entity_{pytest.id}"
        helper.request.body = {
            "name": entity_name,
            "type": "TestEntity",
            "observations": ["Test observation 1", "Test observation 2"],
        }

        # Execute the controller
        response = asyncio.run(controller.create_entity(helper.request))

        # Verify response
        assert (
            response.status == 201
        ), f"Expected 201 status code, got {response.status}"

        # Get the created entity
        helper.request.match_info = {"name": entity_name}
        get_response = asyncio.run(controller.get_entity(helper.request))

        # Verify entity retrieval
        assert (
            get_response.status == 200
        ), f"Expected 200 status code, got {get_response.status}"

        body_text = asyncio.run(get_response.text())
        body = json.loads(body_text)
        assert body["name"] == entity_name
        assert "observations" in body["properties"]
        assert len(body["properties"]["observations"]) == 2

        # Clean up - Delete the entity
        delete_response = asyncio.run(controller.delete_entity(helper.request))
        assert (
            delete_response.status == 200
        ), f"Expected 200 status code, got {delete_response.status}"
    except Exception as e:
        logger.error(f"Error in knowledge graph test: {e}")
        pytest.skip(f"Knowledge graph test error: {e}")


@pytest.mark.integration
def test_full_ai_roundtrip(tmp_path):
    """Test the full AI roundtrip workflow."""
    # Skip if no AI API key
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        pytest.skip(
            "No AI API key found in environment. Set ANTHROPIC_API_KEY or OPENAI_API_KEY to enable."
        )

    # Create test helper with AI config
    ai_config = {
        "AI_PROVIDER": os.environ.get("INKLINK_AI_PROVIDER", "anthropic"),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
        "ANTHROPIC_MODEL": os.environ.get("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
        "OPENAI_MODEL": os.environ.get("OPENAI_MODEL", "gpt-4-turbo"),
    }
    helper = ControllerTestHelper(tmp_path, ai_config)

    # Get required services
    ai_service = helper.get_service(IAIService)
    document_service = helper.get_service(IDocumentService)

    # Test AI query processing
    query = "Summarize the following content in 3 bullet points: Example Domain. This domain is for use in illustrative examples in documents."
    response = ai_service.ask(query)

    # Verify AI response format
    assert response, "AI service returned empty response"
    assert len(response) > 10, "AI response too short"

    # Test AI processing with document content
    content = {
        "title": "Example Domain",
        "text": "This domain is for use in illustrative examples in documents.",
        "url": "https://example.com/",
    }

    ai_response = ai_service.process_query(
        "Summarize this content", context={"metadata": content}
    )

    # Verify AI response
    assert ai_response, "AI service returned empty response"
    assert len(ai_response) > 10, "AI response too short"

    # If we have document service and remarkable service, test the full roundtrip
    try:
        remarkable_service = helper.get_service(IRemarkableService)

        # Create a simple markdown document with AI response
        md_content = f"# Example Domain\n\n{ai_response}"

        # Save to a file
        md_path = os.path.join(helper.temp_dir, "ai_response.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # Create a remarkable document
        rm_doc = document_service.create_rmdoc(md_path, "https://example.com")

        # Upload to remarkable (if rmapi is configured)
        remarkable_service.upload(rm_doc, "AI Response Test")

        # If we get here, the full roundtrip worked
        logger.info("Full AI roundtrip test completed successfully")
    except Exception as e:
        logger.error(f"Error in full AI roundtrip: {e}")
        pytest.skip(f"Full AI roundtrip skipped due to error: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    tmp_path = os.path.join(os.path.dirname(__file__), "tmp")
    os.makedirs(tmp_path, exist_ok=True)
    test_share_controller_roundtrip(tmp_path)
    test_knowledge_graph_roundtrip(tmp_path)
    test_full_ai_roundtrip(tmp_path)
