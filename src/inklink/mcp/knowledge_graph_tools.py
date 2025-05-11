"""
MCP Knowledge Graph tools for InkLink.

This module provides MCP-compatible functions for interacting with the
Neo4j knowledge graph. These tools can be used by Claude and other
MCP-compatible interfaces.
"""

import logging
from typing import Dict, Any

from inklink.di.container import Container
from inklink.services.knowledge_graph_service import KnowledgeGraphService
from inklink.mcp.knowledge_graph_tools_integration import KnowledgeGraphMCPIntegration

logger = logging.getLogger(__name__)


def initialize_kg_integration():
    """
    Initialize the Knowledge Graph integration with MCP.

    Returns:
        KnowledgeGraphMCPIntegration instance
    """
    # Initialize the dependency injection container
    config = {}  # This would normally be populated from environment
    provider = Container.create_provider(config)

    # Get the knowledge graph service
    kg_service = provider.get(KnowledgeGraphService)

    # Create the MCP integration
    return KnowledgeGraphMCPIntegration(kg_service)


# Initialize the integration once
_kg_integration = None


def get_kg_integration():
    """
    Get the Knowledge Graph MCP integration instance.

    Returns:
        KnowledgeGraphMCPIntegration instance
    """
    global _kg_integration
    if _kg_integration is None:
        _kg_integration = initialize_kg_integration()
    return _kg_integration
