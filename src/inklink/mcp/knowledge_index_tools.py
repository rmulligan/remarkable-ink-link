"""
MCP tools for knowledge index notebooks.

This module integrates the knowledge index service with Model Context Protocol (MCP)
tools, enabling Claude and other MCP-compatible interfaces to create and manage
index notebooks that organize entities and topics with references to related content.
"""

import logging
from typing import Any, Dict, List, Optional

from inklink.di.container import Container
from inklink.services.knowledge_index_service import KnowledgeIndexService

logger = logging.getLogger(__name__)


class KnowledgeIndexMCPIntegration:
    """
    Integration of knowledge index service with MCP tools.

    This class provides MCP-compatible functions for creating and managing
    knowledge index notebooks that organize content for easy reference.
    """

    def __init__(self, knowledge_index_service: KnowledgeIndexService):
        """
        Initialize the MCP integration.

        Args:
            knowledge_index_service: Service for knowledge index functionality
        """
        self.knowledge_index_service = knowledge_index_service

    def create_entity_index(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an entity index notebook.

        Args:
            params: Dictionary with the following keys:
                - entity_types: Optional list of entity types to include
                - min_references: Minimum number of references (default: 1)
                - upload_to_remarkable: Whether to upload to reMarkable (default: true)

        Returns:
            Result dictionary
        """
        # Get parameters
        entity_types = params.get("entity_types")
        min_references = params.get("min_references", 1)
        upload_to_remarkable = params.get("upload_to_remarkable", True)

        # Create the entity index
        success, result = self.knowledge_index_service.create_entity_index(
            entity_types=entity_types,
            min_references=min_references,
            upload_to_remarkable=upload_to_remarkable,
        )

        if not success:
            return {"success": False, "error": result.get("error", "Creation failed")}

        # Return summarized result
        return {
            "success": True,
            "entity_count": result.get("entity_count", 0),
            "entity_types": result.get("entity_types", []),
            "document_path": result.get("document_path"),
            "uploaded": result.get("upload_result", {}).get("success", False),
            "title": result.get("upload_result", {}).get("title", ""),
        }

    def create_topic_index(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a topic index notebook.

        Args:
            params: Dictionary with the following keys:
                - top_n_topics: Number of top topics (default: 20)
                - min_connections: Minimum connections (default: 2)
                - upload_to_remarkable: Whether to upload to reMarkable (default: true)

        Returns:
            Result dictionary
        """
        # Get parameters
        top_n_topics = params.get("top_n_topics", 20)
        min_connections = params.get("min_connections", 2)
        upload_to_remarkable = params.get("upload_to_remarkable", True)

        # Create the topic index
        success, result = self.knowledge_index_service.create_topic_index(
            top_n_topics=top_n_topics,
            min_connections=min_connections,
            upload_to_remarkable=upload_to_remarkable,
        )

        if not success:
            return {"success": False, "error": result.get("error", "Creation failed")}

        # Return summarized result
        return {
            "success": True,
            "topic_count": result.get("topic_count", 0),
            "document_path": result.get("document_path"),
            "uploaded": result.get("upload_result", {}).get("success", False),
            "title": result.get("upload_result", {}).get("title", ""),
        }

    def create_notebook_index(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a notebook content index.

        Args:
            params: Dictionary with the following keys:
                - upload_to_remarkable: Whether to upload to reMarkable (default: true)

        Returns:
            Result dictionary
        """
        # Get parameters
        upload_to_remarkable = params.get("upload_to_remarkable", True)

        # Create the notebook index
        success, result = self.knowledge_index_service.create_notebook_index(
            upload_to_remarkable=upload_to_remarkable
        )

        if not success:
            return {"success": False, "error": result.get("error", "Creation failed")}

        # Return summarized result
        return {
            "success": True,
            "notebook_count": result.get("notebook_count", 0),
            "document_path": result.get("document_path"),
            "uploaded": result.get("upload_result", {}).get("success", False),
            "title": result.get("upload_result", {}).get("title", ""),
        }

    def create_master_index(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a master index notebook containing entity, topic, and notebook indices.

        Args:
            params: Dictionary with the following keys:
                - upload_to_remarkable: Whether to upload to reMarkable (default: true)

        Returns:
            Result dictionary
        """
        # Get parameters
        upload_to_remarkable = params.get("upload_to_remarkable", True)

        # Create the master index
        success, result = self.knowledge_index_service.create_master_index(
            upload_to_remarkable=upload_to_remarkable
        )

        if not success:
            return {"success": False, "error": result.get("error", "Creation failed")}

        # Return summarized result
        return {
            "success": True,
            "entity_count": result.get("entity_count", 0),
            "topic_count": result.get("topic_count", 0),
            "notebook_count": result.get("notebook_count", 0),
            "document_path": result.get("document_path"),
            "uploaded": result.get("upload_result", {}).get("success", False),
            "title": result.get("upload_result", {}).get("title", ""),
        }


# MCP tool handler functions (for direct use with MCP server)


def create_entity_index(params):
    """MCP handler for creating an entity index notebook."""
    config = {}  # This would be populated in a real implementation
    provider = Container.create_provider(config)
    knowledge_index_service = provider.get(KnowledgeIndexService)
    mcp = KnowledgeIndexMCPIntegration(knowledge_index_service)
    return mcp.create_entity_index(params)


def create_topic_index(params):
    """MCP handler for creating a topic index notebook."""
    config = {}  # This would be populated in a real implementation
    provider = Container.create_provider(config)
    knowledge_index_service = provider.get(KnowledgeIndexService)
    mcp = KnowledgeIndexMCPIntegration(knowledge_index_service)
    return mcp.create_topic_index(params)


def create_notebook_index(params):
    """MCP handler for creating a notebook content index."""
    config = {}  # This would be populated in a real implementation
    provider = Container.create_provider(config)
    knowledge_index_service = provider.get(KnowledgeIndexService)
    mcp = KnowledgeIndexMCPIntegration(knowledge_index_service)
    return mcp.create_notebook_index(params)


def create_master_index(params):
    """MCP handler for creating a master index notebook."""
    config = {}  # This would be populated in a real implementation
    provider = Container.create_provider(config)
    knowledge_index_service = provider.get(KnowledgeIndexService)
    mcp = KnowledgeIndexMCPIntegration(knowledge_index_service)
    return mcp.create_master_index(params)
