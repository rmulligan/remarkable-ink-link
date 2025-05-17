"""Limitless Life Log controller for InkLink.

This module provides a controller for handling Limitless Life Log API endpoints.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from inklink.controllers.base_controller import BaseController
from inklink.services.limitless_life_log_service import LimitlessLifeLogService
from inklink.services.limitless_scheduler_service import LimitlessSchedulerService

logger = logging.getLogger(__name__)


class LimitlessController(BaseController):
    """Controller for handling Limitless Life Log API endpoints."""

    def __init__(
        self,
        limitless_service: LimitlessLifeLogService,
        limitless_scheduler: LimitlessSchedulerService,
        handler,
    ):
        """
        Initialize the controller with required services.

        Args:
            limitless_service: Service for managing Limitless Life Logs
            limitless_scheduler: Service for scheduling Limitless syncs
            handler: HTTP handler for request/response
        """
        super().__init__(handler)
        self.limitless_service = limitless_service
        self.limitless_scheduler = limitless_scheduler

    def handle(self, *args, **kwargs) -> None:
        """
        Handle the HTTP request.

        Args:
            *args: Variable positional arguments
            **kwargs: Variable keyword arguments
        """
        # This method delegates to handle_request
        if len(args) >= 4:
            path, method, query, body = args[:4]
            self.handle_request(path, method, query, body)
        else:
            # Default behavior
            self.handle_request("", "GET", {}, {})

    def json_response(self, data: Dict[str, Any], status: int = 200) -> Dict[str, Any]:
        """
        Return JSON response data.

        Args:
            data: Response data
            status: HTTP status code

        Returns:
            Response data (for testing)
        """
        # If we have a handler, send the response
        if hasattr(self, "handler") and self.handler:
            self.send_json(data, status)

        # Return data for testing purposes
        return data

    def handle_request(self, path: str, method: str, query: Dict[str, str], body: Dict):
        """
        Handle HTTP requests for Limitless endpoints.

        Args:
            path: Request path
            method: HTTP method
            query: Request query parameters
            body: Request body data

        Returns:
            Response data
        """
        # Extract endpoint from path
        parts = path.split("/")
        if len(parts) < 3:
            return self.json_response({"error": "Invalid endpoint"}, status=400)

        endpoint = parts[2]  # /limitless/{endpoint}

        # Route request to appropriate handler
        if endpoint == "sync":
            return self.handle_sync(method, query, body)
        if endpoint == "status":
            return self.handle_status(method)
        if endpoint == "logs":
            # Check if this is a request for a specific log
            if len(parts) > 3:
                log_id = parts[3]
                return self.handle_get_log(method, log_id)
            return self.handle_logs(method, query)
        if endpoint == "scheduler":
            return self.handle_scheduler(method, query, body)
        if endpoint == "cache":
            return self.handle_cache(method)
        return self.json_response(
            {"error": f"Unknown endpoint: {endpoint}"}, status=404
        )

    def handle_sync(
        self, method: str, query: Dict[str, str], body: Dict
    ) -> Dict[str, Any]:
        """
        Handle sync operations.

        Args:
            method: HTTP method
            query: Request query parameters
            body: Request body data

        Returns:
            Response data
        """
        if method != "POST":
            return self.json_response({"error": "Method not allowed"}, status=405)

        # Check for force flag
        force_full_sync = query.get("force", "").lower() == "true" or (
            body.get("force_full_sync", False) if body else False
        )

        # Trigger sync via scheduler
        result = self.limitless_scheduler.trigger_sync(force_full_sync=force_full_sync)
        return self.json_response(result)

    def handle_status(self, method: str) -> Dict[str, Any]:
        """
        Handle status requests.

        Args:
            method: HTTP method

        Returns:
            Response data
        """
        if method != "GET":
            return self.json_response({"error": "Method not allowed"}, status=405)

        # Get status from service and scheduler
        service_status = self.limitless_service.get_sync_status()
        scheduler_status = self.limitless_scheduler.get_status()

        # Combine statuses
        status = {
            "service": service_status,
            "scheduler": scheduler_status,
        }

        return self.json_response(status)

    def handle_logs(self, method: str, query: Dict[str, str]) -> Dict[str, Any]:
        """
        Handle log listing/operations.

        Args:
            method: HTTP method
            query: Request query parameters

        Returns:
            Response data
        """
        if method != "GET":
            return self.json_response({"error": "Method not allowed"}, status=405)

        # This endpoint would list available logs from cache
        # Not implemented directly yet - would require additional methods
        # in the service to list cached logs

        return self.json_response(
            {"error": "Listing logs not yet implemented"}, status=501
        )

    def handle_get_log(self, method: str, log_id: str) -> Dict[str, Any]:
        """
        Handle requests for a specific log.

        Args:
            method: HTTP method
            log_id: ID of the log to retrieve

        Returns:
            Response data
        """
        if method != "GET":
            return self.json_response({"error": "Method not allowed"}, status=405)

        # Get the log from the service
        success, result = self.limitless_service.get_life_log(log_id)

        if not success:
            return self.json_response(
                {"error": f"Failed to retrieve log: {result}"}, status=404
            )

        return self.json_response({"log": result})

    def handle_scheduler(
        self, method: str, query: Dict[str, str], body: Dict
    ) -> Dict[str, Any]:
        """
        Handle scheduler operations.

        Args:
            method: HTTP method
            query: Request query parameters
            body: Request body data

        Returns:
            Response data
        """
        if method == "GET":
            # Get scheduler status
            status = self.limitless_scheduler.get_status()
            return self.json_response(status)

        if method == "POST":
            # Extract action from query or body
            action = query.get("action") or (body and body.get("action"))
            if not action:
                return self.json_response(
                    {"error": "Missing action parameter"}, status=400
                )

            # Handle different actions
            if action == "start":
                result = self.limitless_scheduler.start()
                return self.json_response(
                    {"success": result, "message": "Scheduler started"}
                )
            if action == "stop":
                result = self.limitless_scheduler.stop()
                return self.json_response(
                    {"success": result, "message": "Scheduler stopped"}
                )
            return self.json_response(
                {"error": f"Unknown action: {action}"}, status=400
            )
        return self.json_response({"error": "Method not allowed"}, status=405)

    def handle_cache(self, method: str) -> Dict[str, Any]:
        """
        Handle cache operations.

        Args:
            method: HTTP method

        Returns:
            Response data
        """
        if method == "DELETE":
            # Clear cache
            success, message = self.limitless_service.clear_cache()
            return self.json_response({"success": success, "message": message})
        return self.json_response({"error": "Method not allowed"}, status=405)
