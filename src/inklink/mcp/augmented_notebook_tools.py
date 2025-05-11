"""
MCP tools for augmented notebook functionality.

This module integrates the augmented notebook service with Model Context Protocol (MCP)
tools, enabling Claude and other MCP-compatible interfaces to process reMarkable
notebook pages with AI, knowledge graph integration, and response generation.
"""

import logging
import os
from typing import Dict, Any, List, Optional

from inklink.services.augmented_notebook_service import AugmentedNotebookService
from inklink.di.container import Container

logger = logging.getLogger(__name__)


class AugmentedNotebookMCPIntegration:
    """
    Integration of augmented notebook service with MCP tools.

    This class provides MCP-compatible functions for augmented notebook processing,
    allowing Claude to analyze handwritten notes, respond to queries, and add
    results to the knowledge graph.
    """

    def __init__(self, augmented_notebook_service: AugmentedNotebookService):
        """
        Initialize the MCP integration.

        Args:
            augmented_notebook_service: Service for augmented notebook functionality
        """
        self.augmented_notebook_service = augmented_notebook_service

    def process_notebook_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a notebook page with Claude analysis, knowledge graph integration, and response.

        Args:
            params: Dictionary with the following keys:
                - file_path: Path to the .rm file (required)
                - append_response: Whether to append the response to the notebook (optional)
                - extract_knowledge: Whether to extract knowledge to the graph (optional)
                - categorize_correspondence: Whether to categorize the correspondence (optional)

        Returns:
            Result dictionary
        """
        file_path = params.get("file_path")

        if not file_path:
            return {"success": False, "error": "file_path is required"}

        # Validate that the file exists
        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}

        # Get optional parameters
        append_response = params.get("append_response", True)
        extract_knowledge = params.get("extract_knowledge", True)
        categorize_correspondence = params.get("categorize_correspondence", True)

        # Process the notebook page
        success, result = self.augmented_notebook_service.process_notebook_page(
            rm_file_path=file_path,
            append_response=append_response,
            extract_knowledge=extract_knowledge,
            categorize_correspondence=categorize_correspondence,
        )

        if not success:
            return {"success": False, "error": result.get("error", "Processing failed")}

        # Remove large result data to keep MCP response size manageable
        summarized_result = {
            "success": True,
            "recognized_text": result.get("recognized_text", ""),
            "tags": result.get("tags", []),
            "requests": result.get("requests", []),
            "knowledge_extracted": {
                "entity_count": len(
                    result.get("knowledge_extracted", {}).get("entities", [])
                ),
                "relationship_count": len(
                    result.get("knowledge_extracted", {}).get("relationships", [])
                ),
                "semantic_link_count": len(
                    result.get("knowledge_extracted", {}).get("semantic_links", [])
                ),
            },
            "response_generated": bool(
                result.get("claude_processing", {}).get("response")
            ),
            "response_appended": bool(result.get("append_results")),
        }

        if result.get("append_results"):
            summarized_result["response_path"] = result["append_results"].get(
                "response_path"
            )
            summarized_result["response_title"] = result["append_results"].get("title")

        return summarized_result

    def batch_process_notebook_pages(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process multiple notebook pages in batch.

        Args:
            params: Dictionary with the following keys:
                - file_paths: List of paths to .rm files (required)
                - append_response: Whether to append responses (optional)
                - extract_knowledge: Whether to extract knowledge (optional)
                - categorize_correspondence: Whether to categorize correspondence (optional)

        Returns:
            Batch processing results
        """
        file_paths = params.get("file_paths", [])

        if not file_paths:
            return {"success": False, "error": "file_paths is required"}

        # Get optional parameters
        append_response = params.get("append_response", True)
        extract_knowledge = params.get("extract_knowledge", True)
        categorize_correspondence = params.get("categorize_correspondence", True)

        # Process each notebook page
        results = []
        successful = 0
        failed = 0

        for file_path in file_paths:
            # Validate that the file exists
            if not os.path.exists(file_path):
                results.append(
                    {
                        "file_path": file_path,
                        "success": False,
                        "error": "File not found",
                    }
                )
                failed += 1
                continue

            # Process the notebook page
            success, result = self.augmented_notebook_service.process_notebook_page(
                rm_file_path=file_path,
                append_response=append_response,
                extract_knowledge=extract_knowledge,
                categorize_correspondence=categorize_correspondence,
            )

            if success:
                successful += 1
                results.append(
                    {
                        "file_path": file_path,
                        "success": True,
                        "recognized_text": (
                            result.get("recognized_text", "")[:100] + "..."
                            if result.get("recognized_text")
                            else ""
                        ),
                        "response_appended": bool(result.get("append_results")),
                    }
                )
            else:
                failed += 1
                results.append(
                    {
                        "file_path": file_path,
                        "success": False,
                        "error": result.get("error", "Processing failed"),
                    }
                )

        return {
            "success": successful > 0,
            "total": len(file_paths),
            "successful": successful,
            "failed": failed,
            "results": results,
        }


# MCP tool handler functions (for direct use with MCP server)


def process_notebook_page(params):
    """MCP handler for processing a notebook page."""
    config = {}  # This would be populated in a real implementation
    provider = Container.create_provider(config)
    augmented_notebook_service = provider.get(AugmentedNotebookService)
    mcp = AugmentedNotebookMCPIntegration(augmented_notebook_service)
    return mcp.process_notebook_page(params)


def batch_process_notebook_pages(params):
    """MCP handler for batch processing notebook pages."""
    config = {}  # This would be populated in a real implementation
    provider = Container.create_provider(config)
    augmented_notebook_service = provider.get(AugmentedNotebookService)
    mcp = AugmentedNotebookMCPIntegration(augmented_notebook_service)
    return mcp.batch_process_notebook_pages(params)
