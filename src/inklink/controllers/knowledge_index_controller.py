"""
Controller for knowledge index functionality.

This controller provides HTTP endpoints for creating and managing knowledge index
notebooks that organize entities and topics with references to related content.
"""

import logging
import json
from typing import Dict, Any, List, Optional

from inklink.controllers.base_controller import BaseController
from inklink.services.knowledge_index_service import KnowledgeIndexService

logger = logging.getLogger(__name__)


class KnowledgeIndexController(BaseController):
    """
    Controller for knowledge index functionality.

    This controller handles the following operations:
    - Creating entity index notebooks
    - Creating topic index notebooks
    - Creating notebook content index
    - Creating master index notebooks
    """

    def __init__(
        self, knowledge_index_service: KnowledgeIndexService, handler=None
    ):
        """
        Initialize the KnowledgeIndexController.

        Args:
            knowledge_index_service: Service for knowledge index functionality
            handler: Optional HTTP handler for base controller
        """
        super().__init__(handler)
        self.knowledge_index_service = knowledge_index_service
        self._register_routes()

    def _register_routes(self):
        """Register routes for this controller."""
        # Index creation routes
        self.add_route(
            "POST", "/kg/indices/entity", self.create_entity_index
        )
        self.add_route(
            "POST", "/kg/indices/topic", self.create_topic_index
        )
        self.add_route(
            "POST", "/kg/indices/notebook", self.create_notebook_index
        )
        self.add_route(
            "POST", "/kg/indices/master", self.create_master_index
        )

    async def create_entity_index(self, request):
        """
        Create an entity index notebook.

        Request body:
            {
                "entity_types": ["Type1", "Type2"], // Optional
                "min_references": 1, // Optional
                "upload_to_remarkable": true // Optional
            }

        Returns:
            HTTP response with index creation results
        """
        try:
            data = await request.json()

            # Get optional parameters
            entity_types = data.get("entity_types")
            min_references = data.get("min_references", 1)
            upload_to_remarkable = data.get("upload_to_remarkable", True)

            # Create the entity index
            success, result = self.knowledge_index_service.create_entity_index(
                entity_types=entity_types,
                min_references=min_references,
                upload_to_remarkable=upload_to_remarkable
            )

            if not success:
                return self.error_response(
                    result.get("error", "Failed to create entity index"), 400
                )

            return self.json_response(result)

        except json.JSONDecodeError:
            return self.error_response("Invalid JSON", 400)
        except Exception as e:
            logger.error(f"Error creating entity index: {e}")
            return self.error_response(str(e), 500)

    async def create_topic_index(self, request):
        """
        Create a topic index notebook.

        Request body:
            {
                "top_n_topics": 20, // Optional
                "min_connections": 2, // Optional
                "upload_to_remarkable": true // Optional
            }

        Returns:
            HTTP response with index creation results
        """
        try:
            data = await request.json()

            # Get optional parameters
            top_n_topics = data.get("top_n_topics", 20)
            min_connections = data.get("min_connections", 2)
            upload_to_remarkable = data.get("upload_to_remarkable", True)

            # Create the topic index
            success, result = self.knowledge_index_service.create_topic_index(
                top_n_topics=top_n_topics,
                min_connections=min_connections,
                upload_to_remarkable=upload_to_remarkable
            )

            if not success:
                return self.error_response(
                    result.get("error", "Failed to create topic index"), 400
                )

            return self.json_response(result)

        except json.JSONDecodeError:
            return self.error_response("Invalid JSON", 400)
        except Exception as e:
            logger.error(f"Error creating topic index: {e}")
            return self.error_response(str(e), 500)

    async def create_notebook_index(self, request):
        """
        Create a notebook content index.

        Request body:
            {
                "upload_to_remarkable": true // Optional
            }

        Returns:
            HTTP response with index creation results
        """
        try:
            data = await request.json()

            # Get optional parameters
            upload_to_remarkable = data.get("upload_to_remarkable", True)

            # Create the notebook index
            success, result = self.knowledge_index_service.create_notebook_index(
                upload_to_remarkable=upload_to_remarkable
            )

            if not success:
                return self.error_response(
                    result.get("error", "Failed to create notebook index"), 400
                )

            return self.json_response(result)

        except json.JSONDecodeError:
            return self.error_response("Invalid JSON", 400)
        except Exception as e:
            logger.error(f"Error creating notebook index: {e}")
            return self.error_response(str(e), 500)

    async def create_master_index(self, request):
        """
        Create a master index notebook containing entity, topic, and notebook indices.

        Request body:
            {
                "upload_to_remarkable": true // Optional
            }

        Returns:
            HTTP response with index creation results
        """
        try:
            data = await request.json()

            # Get optional parameters
            upload_to_remarkable = data.get("upload_to_remarkable", True)

            # Create the master index
            success, result = self.knowledge_index_service.create_master_index(
                upload_to_remarkable=upload_to_remarkable
            )

            if not success:
                return self.error_response(
                    result.get("error", "Failed to create master index"), 400
                )

            return self.json_response(result)

        except json.JSONDecodeError:
            return self.error_response("Invalid JSON", 400)
        except Exception as e:
            logger.error(f"Error creating master index: {e}")
            return self.error_response(str(e), 500)