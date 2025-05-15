"""Limitless Life Log service for InkLink.

This module provides a service for syncing Limitless Life Logs and integrating
them with the knowledge graph system.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from inklink.adapters.limitless_adapter import LimitlessAdapter
from inklink.services.interfaces import IKnowledgeGraphService, ILimitlessLifeLogService

logger = logging.getLogger(__name__)


class LimitlessLifeLogService(ILimitlessLifeLogService):
    """
    Service for syncing Limitless Life Logs and integrating with knowledge graph.

    This service is responsible for fetching life logs from the Limitless API,
    processing them, and adding the extracted knowledge to the knowledge graph.
    """

    def __init__(
        self,
        limitless_adapter: LimitlessAdapter,
        knowledge_graph_service: IKnowledgeGraphService,
        sync_interval: int = 3600,  # Default to hourly syncing
        storage_path: str = "data/limitless_sync",
    ):
        """
        Initialize the Limitless Life Log service.

        Args:
            limitless_adapter: Adapter for communicating with Limitless API
            knowledge_graph_service: Service for knowledge graph operations
            sync_interval: Interval between automatic syncs in seconds
            storage_path: Path to store sync state and cached life logs
        """
        self.limitless_adapter = limitless_adapter
        self.knowledge_graph_service = knowledge_graph_service
        self.sync_interval = sync_interval
        self.storage_path = storage_path
        self.last_sync_time = None
        self.last_sync_cursor = None

        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)

        # Load sync state
        self._load_sync_state()

    def _load_sync_state(self):
        """Load the previous sync state from disk."""
        state_file = os.path.join(self.storage_path, "sync_state.json")

        if os.path.exists(state_file):
            try:
                with open(state_file, "r") as f:
                    state = json.load(f)

                self.last_sync_time = (
                    datetime.fromisoformat(state.get("last_sync_time"))
                    if state.get("last_sync_time")
                    else None
                )
                self.last_sync_cursor = state.get("last_sync_cursor")

                logger.info(f"Loaded sync state: last sync at {self.last_sync_time}")
            except Exception as e:
                logger.error(f"Error loading sync state: {str(e)}")
                self.last_sync_time = None
                self.last_sync_cursor = None

    def _save_sync_state(self):
        """Save the current sync state to disk."""
        state_file = os.path.join(self.storage_path, "sync_state.json")

        try:
            state = {
                "last_sync_time": (
                    self.last_sync_time.isoformat() if self.last_sync_time else None
                ),
                "last_sync_cursor": self.last_sync_cursor,
            }

            with open(state_file, "w") as f:
                json.dump(state, f)

            logger.info(f"Saved sync state: last sync at {self.last_sync_time}")
        except Exception as e:
            logger.error(f"Error saving sync state: {str(e)}")

    def sync_life_logs(self, force_full_sync: bool = False) -> Tuple[bool, str]:
        """
        Sync life logs from Limitless API to knowledge graph.

        Args:
            force_full_sync: If True, sync all life logs regardless of last sync time

        Returns:
            Tuple of (success, message)
        """
        try:
            # Determine from when to sync
            from_date = None if force_full_sync else self.last_sync_time

            logger.info(
                f"Starting life log sync from {from_date if from_date else 'beginning'}"
            )

            # Get life logs since last sync
            success, life_logs = self.limitless_adapter.get_all_life_logs(
                from_date=from_date
            )

            if not success:
                error_msg = f"Failed to retrieve life logs: {life_logs}"
                logger.error(error_msg)
                return False, error_msg

            if not life_logs:
                logger.info("No new life logs to sync")
                self.last_sync_time = datetime.now()
                self._save_sync_state()
                return True, "No new life logs to sync"

            # Process and add life logs to knowledge graph
            processed_count = 0
            for log in life_logs:
                success, message = self._process_life_log(log)
                if success:
                    processed_count += 1

            # Update sync state
            self.last_sync_time = datetime.now()
            self._save_sync_state()

            result_message = (
                f"Successfully synced {processed_count} of {len(life_logs)} life logs"
            )
            logger.info(result_message)
            return True, result_message

        except Exception as e:
            error_message = f"Error syncing life logs: {str(e)}"
            logger.error(error_message)
            return False, error_message

    def _process_life_log(self, life_log: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Process a single life log and add to knowledge graph.

        Args:
            life_log: Life log data from the Limitless API

        Returns:
            Tuple of (success, message)
        """
        try:
            log_id = life_log.get("id")
            title = life_log.get("title", "Untitled Log")
            content = life_log.get("content", "")
            created_at = life_log.get("created_at")
            metadata = life_log.get("metadata", {})

            logger.info(f"Processing life log: {title} (ID: {log_id})")

            # Save life log to disk for reference
            self._save_life_log(log_id, life_log)

            # Extract entities and relationships from life log content
            entities = self.knowledge_graph_service.extract_entities(content)
            relationships = self.knowledge_graph_service.extract_relationships(content)

            # Create a source entity for this life log
            source_entity = {
                "id": f"lifelog:{log_id}",
                "name": title,
                "type": "LifeLog",
                "source": "Limitless",
                "created_at": created_at,
                "content": content,
                "metadata": metadata,
            }

            # Add source entity to knowledge graph
            success, result = self.knowledge_graph_service.add_entity(source_entity)
            if not success:
                return False, f"Failed to add life log entity: {result}"

            # Add extracted entities and connect to source
            for entity in entities:
                # Add entity
                self.knowledge_graph_service.add_entity(entity)

                # Connect entity to source
                self.knowledge_graph_service.add_relationship(
                    {
                        "from_id": f"lifelog:{log_id}",
                        "to_id": entity["id"],
                        "type": "MENTIONS",
                        "source": "Limitless",
                    }
                )

            # Add extracted relationships
            for relationship in relationships:
                self.knowledge_graph_service.add_relationship(relationship)

            return True, f"Successfully processed life log: {title}"

        except Exception as e:
            error_message = f"Error processing life log: {str(e)}"
            logger.error(error_message)
            return False, error_message

    def _save_life_log(self, log_id: str, life_log: Dict[str, Any]):
        """
        Save life log content to disk for reference.

        Args:
            log_id: ID of the life log
            life_log: Life log data to save
        """
        try:
            logs_dir = os.path.join(self.storage_path, "logs")
            os.makedirs(logs_dir, exist_ok=True)

            log_file = os.path.join(logs_dir, f"{log_id}.json")

            with open(log_file, "w") as f:
                json.dump(life_log, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving life log to disk: {str(e)}")

    def get_life_log(self, log_id: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        Retrieve a specific life log by ID.

        Tries to get from local cache first, then falls back to API.

        Args:
            log_id: ID of the life log to retrieve

        Returns:
            Tuple of (success, life_log_or_error)
        """
        # Try to get from local cache first
        log_file = os.path.join(self.storage_path, "logs", f"{log_id}.json")

        if os.path.exists(log_file):
            try:
                with open(log_file, "r") as f:
                    return True, json.load(f)
            except Exception as e:
                logger.warning(
                    f"Failed to load cached life log, falling back to API: {str(e)}"
                )

        # Fall back to API
        return self.limitless_adapter.get_life_log_by_id(log_id)

    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get the current sync status.

        Returns:
            Dictionary with sync status information
        """
        logs_dir = os.path.join(self.storage_path, "logs")
        cached_log_count = len(os.listdir(logs_dir)) if os.path.exists(logs_dir) else 0

        return {
            "last_sync_time": (
                self.last_sync_time.isoformat() if self.last_sync_time else None
            ),
            "cached_log_count": cached_log_count,
            "sync_interval": self.sync_interval,
            "next_sync_time": (
                (
                    self.last_sync_time + timedelta(seconds=self.sync_interval)
                ).isoformat()
                if self.last_sync_time
                else None
            ),
        }

    def clear_cache(self) -> Tuple[bool, str]:
        """
        Clear the local cache of life logs.

        Returns:
            Tuple of (success, message)
        """
        try:
            logs_dir = os.path.join(self.storage_path, "logs")

            if os.path.exists(logs_dir):
                for filename in os.listdir(logs_dir):
                    file_path = os.path.join(logs_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)

            return True, "Successfully cleared life log cache"

        except Exception as e:
            error_message = f"Error clearing cache: {str(e)}"
            logger.error(error_message)
            return False, error_message
