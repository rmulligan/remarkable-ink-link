"""
Controller for augmented notebook functionality.

This controller provides HTTP endpoints for processing reMarkable notebook pages
with AI assistance, knowledge graph integration, and response generation.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from inklink.controllers.base_controller import BaseController
from inklink.services.augmented_notebook_service import AugmentedNotebookService

logger = logging.getLogger(__name__)


class AugmentedNotebookController(BaseController):
    """
    Controller for augmented notebook functionality.

    This controller handles the following operations:
    - Processing notebook pages with AI and knowledge graph integration
    - Performing tag-driven actions
    - Appending AI-generated responses to notebooks
    """

    def __init__(
        self, augmented_notebook_service: AugmentedNotebookService, handler=None
    ):
        """
        Initialize the AugmentedNotebookController.

        Args:
            augmented_notebook_service: Service for augmented notebook functionality
            handler: Optional HTTP handler for base controller
        """
        super().__init__(handler)
        self.augmented_notebook_service = augmented_notebook_service
        self._register_routes()

    def _register_routes(self):
        """Register routes for this controller."""
        # Process routes
        self.add_route("POST", "/notebooks/process", self.process_notebook_page)

        # Batch process route
        self.add_route(
            "POST", "/notebooks/batch_process", self.batch_process_notebook_pages
        )

        # Configuration route
        self.add_route("GET", "/notebooks/config", self.get_config)
        self.add_route("PUT", "/notebooks/config", self.update_config)

    async def process_notebook_page(self, request):
        """
        Process a notebook page with AI, knowledge graph, and tag-based actions.

        Request body:
            {
                "file_path": "Path to .rm file",
                "append_response": true, // Optional, default: true
                "extract_knowledge": true, // Optional, default: true
                "categorize_correspondence": true // Optional, default: true
            }

        Returns:
            HTTP response with processing results
        """
        try:
            data = await request.json()
            rm_file_path = data.get("file_path")

            if not rm_file_path:
                return self.error_response("file_path is required", 400)

            # Validate that the file exists
            if not os.path.exists(rm_file_path):
                return self.error_response(f"File not found: {rm_file_path}", 404)

            # Get optional parameters
            append_response = data.get("append_response", True)
            extract_knowledge = data.get("extract_knowledge", True)
            categorize_correspondence = data.get("categorize_correspondence", True)

            # Process the notebook page
            success, result = self.augmented_notebook_service.process_notebook_page(
                rm_file_path=rm_file_path,
                append_response=append_response,
                extract_knowledge=extract_knowledge,
                categorize_correspondence=categorize_correspondence,
            )

            if not success:
                return self.error_response(
                    result.get("error", "Failed to process notebook page"), 400
                )

            return self.json_response(result)

        except json.JSONDecodeError:
            return self.error_response("Invalid JSON", 400)
        except Exception as e:
            logger.error(f"Error processing notebook page: {e}")
            return self.error_response(str(e), 500)

    async def batch_process_notebook_pages(self, request):
        """
        Process multiple notebook pages in batch.

        Request body:
            {
                "file_paths": ["Path1", "Path2", ...],
                "append_response": true, // Optional, default: true
                "extract_knowledge": true, // Optional, default: true
                "categorize_correspondence": true // Optional, default: true
            }

        Returns:
            HTTP response with batch processing results
        """
        try:
            data = await request.json()
            rm_file_paths = data.get("file_paths", [])

            if not rm_file_paths:
                return self.error_response("file_paths is required", 400)

            # Get optional parameters
            append_response = data.get("append_response", True)
            extract_knowledge = data.get("extract_knowledge", True)
            categorize_correspondence = data.get("categorize_correspondence", True)

            # Process each notebook page
            results = []

            for file_path in rm_file_paths:
                # Validate that the file exists
                if not os.path.exists(file_path):
                    results.append(
                        {
                            "file_path": file_path,
                            "success": False,
                            "error": "File not found",
                        }
                    )
                    continue

                # Process the notebook page
                success, result = self.augmented_notebook_service.process_notebook_page(
                    rm_file_path=file_path,
                    append_response=append_response,
                    extract_knowledge=extract_knowledge,
                    categorize_correspondence=categorize_correspondence,
                )

                results.append(
                    {"file_path": file_path, "success": success, "result": result}
                )

            return self.json_response(
                {
                    "total": len(rm_file_paths),
                    "successful": sum(1 for r in results if r["success"]),
                    "failed": sum(1 for r in results if not r["success"]),
                    "results": results,
                }
            )

        except json.JSONDecodeError:
            return self.error_response("Invalid JSON", 400)
        except Exception as e:
            logger.error(f"Error batch processing notebook pages: {e}")
            return self.error_response(str(e), 500)

    async def get_config(self, request):
        """
        Get the current configuration for augmented notebook processing.

        Returns:
            HTTP response with configuration settings
        """
        # Get service configuration
        config = {
            "tag_processing": True,
            "web_search_enabled": True,
            "kg_search_enabled": True,
            "default_append_response": True,
            "default_extract_knowledge": True,
            "default_categorize_correspondence": True,
            "claude_model": self.augmented_notebook_service.claude_model,
            "min_entity_confidence": self.augmented_notebook_service.kg_integration_service.min_entity_confidence,
            "min_relation_confidence": self.augmented_notebook_service.kg_integration_service.min_relation_confidence,
            "min_semantic_similarity": self.augmented_notebook_service.kg_integration_service.min_semantic_similarity,
        }

        return self.json_response(config)

    async def update_config(self, request):
        """
        Update the configuration for augmented notebook processing.

        Request body:
            {
                "tag_processing": true,
                "web_search_enabled": true,
                "kg_search_enabled": true,
                "default_append_response": true,
                "default_extract_knowledge": true,
                "default_categorize_correspondence": true,
                "claude_model": "claude-3-5-sonnet",
                "min_entity_confidence": 0.7,
                "min_relation_confidence": 0.7,
                "min_semantic_similarity": 0.6
            }

        Returns:
            HTTP response with updated configuration
        """
        try:
            data = await request.json()

            # Update service attributes for configurable settings
            if "claude_model" in data:
                self.augmented_notebook_service.claude_model = data["claude_model"]

            if "min_entity_confidence" in data:
                self.augmented_notebook_service.kg_integration_service.min_entity_confidence = float(
                    data["min_entity_confidence"]
                )

            if "min_relation_confidence" in data:
                self.augmented_notebook_service.kg_integration_service.min_relation_confidence = float(
                    data["min_relation_confidence"]
                )

            if "min_semantic_similarity" in data:
                self.augmented_notebook_service.kg_integration_service.min_semantic_similarity = float(
                    data["min_semantic_similarity"]
                )

            # Return the updated configuration
            return await self.get_config(request)

        except json.JSONDecodeError:
            return self.error_response("Invalid JSON", 400)
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return self.error_response(str(e), 500)
