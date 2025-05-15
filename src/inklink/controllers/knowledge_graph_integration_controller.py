"""
Controller for integrating knowledge graph capabilities with reMarkable notebooks.

This controller exposes HTTP endpoints for extracting knowledge from reMarkable
notebooks, performing semantic search with handwritten queries, and more.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from inklink.controllers.base_controller import BaseController
from inklink.services.knowledge_graph_integration_service import (
    KnowledgeGraphIntegrationService,
)

logger = logging.getLogger(__name__)


class KnowledgeGraphIntegrationController(BaseController):
    """
    Controller for knowledge graph integration with reMarkable notebooks.

    This controller handles the following operations:
    - Extracting knowledge from handwritten notes
    - Semantic search using handwritten queries
    - Augmenting notebooks with knowledge graph information
    """

    def __init__(
        self,
        knowledge_graph_integration_service: KnowledgeGraphIntegrationService,
        handler=None,
    ):
        """
        Initialize the KnowledgeGraphIntegrationController.

        Args:
            knowledge_graph_integration_service: Service for KG-reMarkable integration
            handler: Optional HTTP handler for base controller
        """
        super().__init__(handler)
        self.kg_integration_service = knowledge_graph_integration_service
        self._register_routes()

    def _register_routes(self):
        """Register routes for this controller."""
        # Knowledge extraction routes
        self.add_route(
            "POST", "/kg/notebooks/extract", self.extract_knowledge_from_notebook
        )

        # Semantic search routes
        self.add_route(
            "POST", "/kg/notebooks/search", self.semantic_search_from_handwritten_query
        )

        # Notebook augmentation route
        self.add_route(
            "POST", "/kg/notebooks/augment", self.augment_notebook_with_knowledge
        )

    async def extract_knowledge_from_notebook(self, request):
        """
        Extract knowledge graph entities and relationships from a reMarkable notebook.

        Request body:
            {
                "file_path": "Path to .rm file",
                "entity_types": ["Type1", "Type2"] // Optional
            }

        Returns:
            HTTP response with extraction results
        """
        try:
            data = await request.json()
            rm_file_path = data.get("file_path")
            entity_types = data.get("entity_types")

            if not rm_file_path:
                return self.error_response("file_path is required", 400)

            # Validate that the file exists
            if not os.path.exists(rm_file_path):
                return self.error_response(f"File not found: {rm_file_path}", 404)

            # Extract knowledge from the notebook
            success, result = (
                self.kg_integration_service.extract_knowledge_from_notebook(
                    rm_file_path=rm_file_path, entity_types=entity_types
                )
            )

            if not success:
                return self.error_response(
                    result.get("error", "Failed to extract knowledge"), 400
                )

            return self.json_response(result)

        except json.JSONDecodeError:
            return self.error_response("Invalid JSON", 400)
        except Exception as e:
            logger.error(f"Error extracting knowledge from notebook: {e}")
            return self.error_response(str(e), 500)

    async def semantic_search_from_handwritten_query(self, request):
        """
        Perform semantic search using a handwritten query from a reMarkable notebook.

        Request body:
            {
                "file_path": "Path to .rm file",
                "min_similarity": 0.6, // Optional
                "max_results": 10, // Optional
                "entity_types": ["Type1", "Type2"] // Optional
            }

        Returns:
            HTTP response with search results
        """
        try:
            data = await request.json()
            rm_file_path = data.get("file_path")
            min_similarity = data.get("min_similarity", 0.6)
            max_results = data.get("max_results", 10)
            entity_types = data.get("entity_types")

            if not rm_file_path:
                return self.error_response("file_path is required", 400)

            # Validate that the file exists
            if not os.path.exists(rm_file_path):
                return self.error_response(f"File not found: {rm_file_path}", 404)

            # Validate parameters
            try:
                min_similarity = float(min_similarity)
                if not 0 <= min_similarity <= 1:
                    return self.error_response(
                        "min_similarity must be between 0 and 1", 400
                    )
            except (ValueError, TypeError):
                return self.error_response(
                    "min_similarity must be a float between 0 and 1", 400
                )

            try:
                max_results = int(max_results)
                if max_results <= 0:
                    return self.error_response(
                        "max_results must be a positive integer", 400
                    )
            except (ValueError, TypeError):
                return self.error_response(
                    "max_results must be a positive integer", 400
                )

            # Perform semantic search
            success, result = (
                self.kg_integration_service.semantic_search_from_handwritten_query(
                    rm_file_path=rm_file_path,
                    min_similarity=min_similarity,
                    max_results=max_results,
                    entity_types=entity_types,
                )
            )

            if not success:
                return self.error_response(
                    result.get("error", "Semantic search failed"), 400
                )

            return self.json_response(result)

        except json.JSONDecodeError:
            return self.error_response("Invalid JSON", 400)
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            return self.error_response(str(e), 500)

    async def augment_notebook_with_knowledge(self, request):
        """
        Augment a reMarkable notebook with knowledge graph information.

        Request body:
            {
                "file_path": "Path to .rm file",
                "include_related": true, // Optional
                "include_semantic": true // Optional
            }

        Returns:
            HTTP response with augmented content
        """
        try:
            data = await request.json()
            rm_file_path = data.get("file_path")
            include_related = data.get("include_related", True)
            include_semantic = data.get("include_semantic", True)

            if not rm_file_path:
                return self.error_response("file_path is required", 400)

            # Validate that the file exists
            if not os.path.exists(rm_file_path):
                return self.error_response(f"File not found: {rm_file_path}", 404)

            # Augment notebook with knowledge
            success, result = (
                self.kg_integration_service.augment_notebook_with_knowledge(
                    rm_file_path=rm_file_path,
                    include_related=include_related,
                    include_semantic=include_semantic,
                )
            )

            if not success:
                return self.error_response(
                    result.get("error", "Failed to augment notebook"), 400
                )

            return self.json_response(result)

        except json.JSONDecodeError:
            return self.error_response("Invalid JSON", 400)
        except Exception as e:
            logger.error(f"Error augmenting notebook: {e}")
            return self.error_response(str(e), 500)
