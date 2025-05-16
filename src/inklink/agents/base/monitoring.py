"""Enhanced monitoring and resilience for agents."""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
import logging

from .agent import LocalAgent, AgentState


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result."""

    status: HealthStatus
    message: str
    timestamp: datetime
    details: Dict[str, any] = field(default_factory=dict)


@dataclass
class AgentMetrics:
    """Metrics for an agent."""

    agent_name: str
    start_time: datetime
    restart_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    health_checks: List[HealthCheck] = field(default_factory=list)
    request_count: int = 0
    request_errors: int = 0
    average_response_time: float = 0.0


class RestartPolicy:
    """Policy for restarting agents."""

    def __init__(
        self,
        max_restarts: int = 3,
        restart_window: timedelta = timedelta(hours=1),
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
    ):
        """Initialize the restart policy."""
        self.max_restarts = max_restarts
        self.restart_window = restart_window
        self.backoff_factor = backoff_factor
        self.initial_delay = initial_delay
        self.restart_history: Dict[str, List[datetime]] = {}

    def should_restart(self, agent_name: str) -> bool:
        """Check if an agent should be restarted based on policy."""
        now = datetime.now()
        history = self.restart_history.get(agent_name, [])

        # Remove old entries outside the window
        recent_restarts = [
            timestamp for timestamp in history if now - timestamp < self.restart_window
        ]

        # Update history
        self.restart_history[agent_name] = recent_restarts

        return len(recent_restarts) < self.max_restarts

    def get_restart_delay(self, agent_name: str) -> float:
        """Get the delay before next restart attempt."""
        history = self.restart_history.get(agent_name, [])
        attempt = len(history)

        # Exponential backoff
        delay = self.initial_delay * (self.backoff_factor**attempt)
        return min(delay, 300)  # Cap at 5 minutes

    def record_restart(self, agent_name: str):
        """Record a restart attempt."""
        if agent_name not in self.restart_history:
            self.restart_history[agent_name] = []

        self.restart_history[agent_name].append(datetime.now())


class MonitoringService:
    """Enhanced monitoring service for agents."""

    def __init__(
        self,
        health_check_interval: float = 30.0,
        metrics_retention: timedelta = timedelta(days=7),
    ):
        """Initialize the monitoring service."""
        self.logger = logging.getLogger("agent.monitoring")
        self.health_check_interval = health_check_interval
        self.metrics_retention = metrics_retention
        self.metrics: Dict[str, AgentMetrics] = {}
        self.restart_policy = RestartPolicy()
        self._running = False

    def get_or_create_metrics(self, agent_name: str) -> AgentMetrics:
        """Get or create metrics for an agent."""
        if agent_name not in self.metrics:
            self.metrics[agent_name] = AgentMetrics(
                agent_name=agent_name, start_time=datetime.now()
            )
        return self.metrics[agent_name]

    async def check_agent_health(self, agent: LocalAgent) -> HealthCheck:
        """Perform health check on an agent."""
        try:
            # Basic state check
            if agent.get_state() == AgentState.ERROR:
                return HealthCheck(
                    status=HealthStatus.UNHEALTHY,
                    message="Agent in error state",
                    timestamp=datetime.now(),
                )

            if agent.get_state() != AgentState.RUNNING:
                return HealthCheck(
                    status=HealthStatus.DEGRADED,
                    message=f"Agent in {agent.get_state()} state",
                    timestamp=datetime.now(),
                )

            # If agent has health_check method, use it
            if hasattr(agent, "health_check"):
                health_result = await agent.health_check()
                return HealthCheck(
                    status=health_result.get("status", HealthStatus.UNKNOWN),
                    message=health_result.get("message", ""),
                    timestamp=datetime.now(),
                    details=health_result.get("details", {}),
                )

            # Default healthy status
            return HealthCheck(
                status=HealthStatus.HEALTHY,
                message="Agent running",
                timestamp=datetime.now(),
            )

        except Exception as e:
            self.logger.error(f"Error checking health for {agent.config.name}: {e}")
            return HealthCheck(
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now(),
            )

    def record_error(self, agent_name: str, error: Exception):
        """Record an error for an agent."""
        metrics = self.get_or_create_metrics(agent_name)
        metrics.error_count += 1
        metrics.last_error = str(error)
        metrics.last_error_time = datetime.now()

    def record_request(self, agent_name: str, duration: float, success: bool):
        """Record a request for an agent."""
        metrics = self.get_or_create_metrics(agent_name)
        metrics.request_count += 1

        if not success:
            metrics.request_errors += 1

        # Update average response time
        if metrics.request_count == 1:
            metrics.average_response_time = duration
        else:
            # Rolling average
            metrics.average_response_time = (
                metrics.average_response_time * (metrics.request_count - 1) + duration
            ) / metrics.request_count

    def get_agent_status_summary(self, agent_name: str) -> Dict[str, any]:
        """Get a status summary for an agent."""
        metrics = self.metrics.get(agent_name)
        if not metrics:
            return {"status": "unknown", "message": "No metrics available"}

        # Determine overall status
        recent_health_checks = [
            check
            for check in metrics.health_checks
            if datetime.now() - check.timestamp < timedelta(minutes=5)
        ]

        if not recent_health_checks:
            overall_status = HealthStatus.UNKNOWN
        else:
            latest_check = recent_health_checks[-1]
            overall_status = latest_check.status

        return {
            "status": overall_status.value,
            "uptime": str(datetime.now() - metrics.start_time),
            "restart_count": metrics.restart_count,
            "error_count": metrics.error_count,
            "request_count": metrics.request_count,
            "request_error_rate": (
                metrics.request_errors / metrics.request_count
                if metrics.request_count > 0
                else 0
            ),
            "average_response_time": metrics.average_response_time,
            "last_error": metrics.last_error,
            "last_error_time": (
                metrics.last_error_time.isoformat() if metrics.last_error_time else None
            ),
        }

    def cleanup_old_metrics(self):
        """Clean up old metrics data."""
        now = datetime.now()

        for agent_name, metrics in self.metrics.items():
            # Remove old health checks
            metrics.health_checks = [
                check
                for check in metrics.health_checks
                if now - check.timestamp < self.metrics_retention
            ]
