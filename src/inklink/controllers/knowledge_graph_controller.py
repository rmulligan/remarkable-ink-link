"""Controller for knowledge graph-related HTTP endpoints."""

import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from inklink.controllers.base_controller import BaseController
from inklink.di.service_provider import ServiceProvider
from inklink.services.interfaces import IKnowledgeGraphService, IKnowledgeIndexService

logger = logging.getLogger(__name__)


class KnowledgeGraphController(BaseController):
    """Controller for knowledge graph-related HTTP endpoints."""

    def __init__(
        self,
        service_provider: ServiceProvider,
        knowledge_graph_service: Optional[IKnowledgeGraphService] = None,
        knowledge_index_service: Optional[IKnowledgeIndexService] = None,
    ):
        """
        Initialize KnowledgeGraphController.

        Args:
            service_provider: Dependency injection service provider
            knowledge_graph_service: Optional manually provided knowledge graph service
            knowledge_index_service: Optional manually provided knowledge index service
        """
        super().__init__(service_provider)
        self.knowledge_graph_service = (
            knowledge_graph_service or service_provider.resolve(IKnowledgeGraphService)
        )
        self.knowledge_index_service = (
            knowledge_index_service or service_provider.resolve(IKnowledgeIndexService)
        )

    async def get_entities_endpoint(
        self,
        request: Request,
        entity_type: Optional[str] = None,
        min_references: int = 0,
    ):
        """
        Get entities from the knowledge graph.

        Args:
            request: FastAPI request object
            entity_type: Optional entity type to filter by
            min_references: Minimum number of references for an entity to be included

        Returns:
            JSON response with entities
        """
        try:
            types = [entity_type] if entity_type else None
            entities = self.knowledge_graph_service.get_entities(
                types=types, min_references=min_references
            )
            return JSONResponse(
                content={
                    "status": "success",
                    "entities": entities,
                    "count": len(entities),
                }
            )
        except Exception as e:
            logger.error(f"Error getting entities: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error getting entities: {str(e)}"
            )

    async def get_topics_endpoint(
        self, request: Request, limit: int = 20, min_connections: int = 2
    ):
        """
        Get topics from the knowledge graph.

        Args:
            request: FastAPI request object
            limit: Maximum number of topics to return
            min_connections: Minimum number of connections for a topic to be included

        Returns:
            JSON response with topics
        """
        try:
            topics = self.knowledge_graph_service.get_topics(
                limit=limit, min_connections=min_connections
            )
            return JSONResponse(
                content={"status": "success", "topics": topics, "count": len(topics)}
            )
        except Exception as e:
            logger.error(f"Error getting topics: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error getting topics: {str(e)}"
            )

    async def get_notebooks_endpoint(self, request: Request):
        """
        Get notebooks from the knowledge graph.

        Args:
            request: FastAPI request object

        Returns:
            JSON response with notebooks
        """
        try:
            notebooks = self.knowledge_graph_service.get_notebooks()
            return JSONResponse(
                content={
                    "status": "success",
                    "notebooks": notebooks,
                    "count": len(notebooks),
                }
            )
        except Exception as e:
            logger.error(f"Error getting notebooks: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error getting notebooks: {str(e)}"
            )

    async def create_entity_index_endpoint(
        self,
        request: Request,
        entity_types: Optional[List[str]] = None,
        min_references: int = 1,
        upload_to_remarkable: bool = True,
    ):
        """
        Create an entity index notebook.

        Args:
            request: FastAPI request object
            entity_types: Optional list of entity types to include
            min_references: Minimum number of references for an entity to be included
            upload_to_remarkable: Whether to upload to reMarkable Cloud

        Returns:
            JSON response with index information
        """
        try:
            success, result = self.knowledge_index_service.create_entity_index(
                entity_types=entity_types,
                min_references=min_references,
                upload_to_remarkable=upload_to_remarkable,
            )

            if not success:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "error": result.get("error", "Unknown error"),
                    },
                )

            return JSONResponse(content={"status": "success", "result": result})
        except Exception as e:
            logger.error(f"Error creating entity index: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating entity index: {str(e)}"
            )

    async def create_topic_index_endpoint(
        self,
        request: Request,
        top_n_topics: int = 20,
        min_connections: int = 2,
        upload_to_remarkable: bool = True,
    ):
        """
        Create a topic index notebook.

        Args:
            request: FastAPI request object
            top_n_topics: Number of top topics to include
            min_connections: Minimum connections for a topic to be included
            upload_to_remarkable: Whether to upload to reMarkable Cloud

        Returns:
            JSON response with index information
        """
        try:
            success, result = self.knowledge_index_service.create_topic_index(
                top_n_topics=top_n_topics,
                min_connections=min_connections,
                upload_to_remarkable=upload_to_remarkable,
            )

            if not success:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "error": result.get("error", "Unknown error"),
                    },
                )

            return JSONResponse(content={"status": "success", "result": result})
        except Exception as e:
            logger.error(f"Error creating topic index: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating topic index: {str(e)}"
            )

    async def create_notebook_index_endpoint(
        self,
        request: Request,
        upload_to_remarkable: bool = True,
    ):
        """
        Create a notebook index.

        Args:
            request: FastAPI request object
            upload_to_remarkable: Whether to upload to reMarkable Cloud

        Returns:
            JSON response with index information
        """
        try:
            success, result = self.knowledge_index_service.create_notebook_index(
                upload_to_remarkable=upload_to_remarkable,
            )

            if not success:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "error": result.get("error", "Unknown error"),
                    },
                )

            return JSONResponse(content={"status": "success", "result": result})
        except Exception as e:
            logger.error(f"Error creating notebook index: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating notebook index: {str(e)}"
            )

    async def create_master_index_endpoint(
        self,
        request: Request,
        upload_to_remarkable: bool = True,
    ):
        """
        Create a master index.

        Args:
            request: FastAPI request object
            upload_to_remarkable: Whether to upload to reMarkable Cloud

        Returns:
            JSON response with index information
        """
        try:
            success, result = self.knowledge_index_service.create_master_index(
                upload_to_remarkable=upload_to_remarkable,
            )

            if not success:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "error": result.get("error", "Unknown error"),
                    },
                )

            return JSONResponse(content={"status": "success", "result": result})
        except Exception as e:
            logger.error(f"Error creating master index: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating master index: {str(e)}"
            )
