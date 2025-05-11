"""Limitless Life Log adapter for InkLink.

This module provides an adapter for integrating with the Limitless Life Log API.
It handles authentication, pagination, and error handling for API requests.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple, Union, Callable
from datetime import datetime, timedelta
import requests

from inklink.adapters.adapter import Adapter
from inklink.adapters.http_adapter import HTTPAdapter

logger = logging.getLogger(__name__)


class LimitlessAdapter(Adapter):
    """Adapter for integrating with the Limitless Life Log API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.limitless.ai",
        timeout: int = 10,
        retries: int = 3,
    ):
        """
        Initialize the Limitless adapter with API credentials.

        Args:
            api_key: API key for Limitless API authentication
            base_url: Base URL for the Limitless API
            timeout: Request timeout in seconds
            retries: Number of retries for failed requests
        """
        self.api_key = api_key
        self.base_url = base_url
        self.http_adapter = HTTPAdapter(base_url, timeout, retries)

    def ping(self) -> bool:
        """
        Check if the Limitless API is reachable.

        Returns:
            True if reachable, False otherwise
        """
        headers = self._get_auth_headers()
        success, _ = self.http_adapter.get(
            "/v1/lifelogs", headers=headers, params={"limit": 1}
        )
        return success

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.

        Returns:
            Dictionary of headers including authentication
        """
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def get_life_logs(
        self,
        limit: int = 10,
        cursor: Optional[str] = None,
        from_date: Optional[datetime] = None,
    ) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        Get life logs from the Limitless API with pagination support.

        Args:
            limit: Maximum number of logs to retrieve (max 10)
            cursor: Pagination cursor from previous request
            from_date: Only retrieve logs created after this date

        Returns:
            Tuple of (success, life_logs_or_error)
        """
        params = {"limit": min(limit, 10)}  # API limit is 10 per request

        if cursor:
            params["cursor"] = cursor

        if from_date:
            params["from"] = from_date.isoformat()

        headers = self._get_auth_headers()
        return self.http_adapter.get("/v1/lifelogs", params=params, headers=headers)

    def get_life_log_by_id(
        self, life_log_id: str
    ) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        Get a specific life log by ID.

        Args:
            life_log_id: ID of the life log to retrieve

        Returns:
            Tuple of (success, life_log_or_error)
        """
        headers = self._get_auth_headers()
        return self.http_adapter.get(f"/v1/lifelogs/{life_log_id}", headers=headers)

    def get_all_life_logs(
        self, from_date: Optional[datetime] = None
    ) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        Get all life logs with automatic pagination handling.

        Args:
            from_date: Only retrieve logs created after this date

        Returns:
            Tuple of (success, all_life_logs_or_error)
        """
        all_logs = []
        cursor = None
        limit = 10  # API maximum per page

        while True:
            success, result = self.get_life_logs(
                limit=limit, cursor=cursor, from_date=from_date
            )

            if not success:
                return False, result

            # Extract logs and cursor from response
            logs = result.get("data", [])
            all_logs.extend(logs)

            # Check if there are more pages
            pagination = result.get("pagination", {})
            cursor = pagination.get("next_cursor")

            if not cursor:
                break

        return True, all_logs
