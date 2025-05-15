"""
MCP integration for knowledge graph and reMarkable notebook integration.

This module integrates the knowledge graph integration service with Model Context
Protocol (MCP) tools, enabling Claude and other MCP-compatible interfaces to
interact with reMarkable notebooks and the knowledge graph.
"""

import logging
from typing import Dict, Any, List, Optional

from inklink.services.knowledge_graph_integration_service import (
    KnowledgeGraphIntegrationService,
)
from inklink.di.container import Container

logger = logging.getLogger(__name__)


class KnowledgeGraphRemarkableMCPIntegration:
    """
    Integration of knowledge graph and reMarkable notebook services with MCP tools.

    This class provides MCP-compatible functions for knowledge graph and reMarkable
    notebook operations, allowing Claude to extract knowledge from handwritten notes
    and perform semantic search using handwritten queries.
    """

    def __init__(self, kg_integration_service: KnowledgeGraphIntegrationService):
        """
        Initialize the MCP integration.

        Args:
            kg_integration_service: Service for KG-reMarkable integration
        """
        self.kg_integration_service = kg_integration_service

    def extract_knowledge_from_notebook(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract knowledge from a reMarkable notebook.

        Args:
            params: Dictionary with the following keys:
                - file_path: Path to the .rm file (required)
                - entity_types: Optional list of entity types to filter by

        Returns:
            Result dictionary
        """
        file_path = params.get("file_path")
        entity_types = params.get("entity_types")

        if not file_path:
            return {"success": False, "error": "file_path is required"}

        # Extract knowledge from the notebook
        success, result = self.kg_integration_service.extract_knowledge_from_notebook(
            rm_file_path=file_path, entity_types=entity_types
        )

        if not success:
            return {"success": False, "error": result.get("error", "Extraction failed")}

        return {
            "success": True,
            "recognized_text": result.get("recognized_text"),
            "entities_count": len(result.get("created_entities", [])),
            "relationships_count": len(result.get("created_relationships", [])),
            "semantic_links_count": len(result.get("semantic_links", [])),
            "entities": result.get("created_entities", []),
            "relationships": result.get("created_relationships", []),
            "semantic_links": result.get("semantic_links", []),
        }

    def semantic_search_from_handwritten_query(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform semantic search using a handwritten query.

        Args:
            params: Dictionary with the following keys:
                - file_path: Path to the .rm file with handwritten query (required)
                - min_similarity: Minimum similarity threshold (0-1)
                - max_results: Maximum number of results to return
                - entity_types: Optional list of entity types to filter by

        Returns:
            Result dictionary
        """
        file_path = params.get("file_path")
        min_similarity = params.get("min_similarity", 0.6)
        max_results = params.get("max_results", 10)
        entity_types = params.get("entity_types")

        if not file_path:
            return {"success": False, "error": "file_path is required"}

        # Perform semantic search
        success, result = (
            self.kg_integration_service.semantic_search_from_handwritten_query(
                rm_file_path=file_path,
                min_similarity=min_similarity,
                max_results=max_results,
                entity_types=entity_types,
            )
        )

        if not success:
            return {
                "success": False,
                "error": result.get("error", "Semantic search failed"),
            }

        return {
            "success": True,
            "query": result.get("query"),
            "results": result.get("search_results", []),
            "count": result.get("result_count", 0),
        }

    def augment_notebook_with_knowledge(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Augment a reMarkable notebook with knowledge graph information.

        Args:
            params: Dictionary with the following keys:
                - file_path: Path to the .rm file with handwritten notes (required)
                - include_related: Whether to include related entities (default: true)
                - include_semantic: Whether to include semantic entities (default: true)

        Returns:
            Result dictionary
        """
        file_path = params.get("file_path")
        include_related = params.get("include_related", True)
        include_semantic = params.get("include_semantic", True)

        if not file_path:
            return {"success": False, "error": "file_path is required"}

        # Augment notebook with knowledge
        success, result = self.kg_integration_service.augment_notebook_with_knowledge(
            rm_file_path=file_path,
            include_related=include_related,
            include_semantic=include_semantic,
        )

        if not success:
            return {
                "success": False,
                "error": result.get("error", "Augmentation failed"),
            }

        return {
            "success": True,
            "original_text": result.get("original_text"),
            "entities": result.get("entities", []),
            "summary": result.get("summary"),
        }


# MCP tool handler functions (for direct use with MCP server)


def extract_knowledge_from_notebook(params):
    """MCP handler for extracting knowledge from a reMarkable notebook."""
    config = {}  # This would be populated in a real implementation
    provider = Container.create_provider(config)
    kg_integration_service = provider.get(KnowledgeGraphIntegrationService)
    mcp = KnowledgeGraphRemarkableMCPIntegration(kg_integration_service)
    return mcp.extract_knowledge_from_notebook(params)


def semantic_search_from_handwritten_query(params):
    """MCP handler for performing semantic search from a handwritten query."""
    config = {}  # This would be populated in a real implementation
    provider = Container.create_provider(config)
    kg_integration_service = provider.get(KnowledgeGraphIntegrationService)
    mcp = KnowledgeGraphRemarkableMCPIntegration(kg_integration_service)
    return mcp.semantic_search_from_handwritten_query(params)


def augment_notebook_with_knowledge(params):
    """MCP handler for augmenting a notebook with knowledge graph information."""
    config = {}  # This would be populated in a real implementation
    provider = Container.create_provider(config)
    kg_integration_service = provider.get(KnowledgeGraphIntegrationService)
    mcp = KnowledgeGraphRemarkableMCPIntegration(kg_integration_service)
    return mcp.augment_notebook_with_knowledge(params)
