"""Enhanced monitoring and resilience for agents."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .agent import AgentState, LocalAgent


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class RestartPolicy(Enum):
    """Restart policy for agents."""

    ALWAYS = "always"
    ON_FAILURE = "on_failure"
    NEVER = "never"


@dataclass
class HealthCheck:
    """Health check result."""

    status: HealthStatus
    message: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


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


class MonitoredAgent(LocalAgent):
    """Agent with enhanced monitoring capabilities."""

    def __init__(self, *args, **kwargs):
        """Initialize monitored agent."""
        super().__init__(*args, **kwargs)
        self._metrics = AgentMetrics(
            agent_name=self.config.name, start_time=datetime.now()
        )
        self._monitor_logger = logging.getLogger(f"agent.{self.config.name}.monitoring")

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request with monitoring."""
        start_time = datetime.now()
        self._metrics.request_count += 1

        try:
            response = await super().handle_request(request)
            response_time = (datetime.now() - start_time).total_seconds()
            self._update_response_time(response_time)
            return response

        except Exception as e:
            self._metrics.request_errors += 1
            self._metrics.error_count += 1
            self._metrics.last_error = str(e)
            self._metrics.last_error_time = datetime.now()
            self._monitor_logger.error(f"Request handling error: {e}")
            raise

    def _update_response_time(self, response_time: float) -> None:
        """Update average response time."""
        total_time = self._metrics.average_response_time * (
            self._metrics.request_count - self._metrics.request_errors - 1
        )
        total_time += response_time
        self._metrics.average_response_time = total_time / (
            self._metrics.request_count - self._metrics.request_errors
        )

    async def _perform_health_check(self) -> HealthCheck:
        """Perform health check on the agent."""
        try:
            # Check agent state
            if self.state == AgentState.ERROR:
                return HealthCheck(
                    status=HealthStatus.UNHEALTHY,
                    message="Agent is in error state",
                    timestamp=datetime.now(),
                    details={"state": self.state.value},
                )

            # Check error rate
            if self._metrics.request_count > 0:
                error_rate = self._metrics.request_errors / self._metrics.request_count
                if error_rate > 0.5:
                    return HealthCheck(
                        status=HealthStatus.UNHEALTHY,
                        message="High error rate",
                        timestamp=datetime.now(),
                        details={
                            "error_rate": error_rate,
                            "request_count": self._metrics.request_count,
                            "request_errors": self._metrics.request_errors,
                        },
                    )
                if error_rate > 0.2:
                    return HealthCheck(
                        status=HealthStatus.DEGRADED,
                        message="Elevated error rate",
                        timestamp=datetime.now(),
                        details={
                            "error_rate": error_rate,
                            "request_count": self._metrics.request_count,
                            "request_errors": self._metrics.request_errors,
                        },
                    )

            # Check response time
            if self._metrics.average_response_time > self.config.timeout_seconds * 0.8:
                return HealthCheck(
                    status=HealthStatus.DEGRADED,
                    message="High response time",
                    timestamp=datetime.now(),
                    details={
                        "average_response_time": self._metrics.average_response_time,
                        "timeout_seconds": self.config.timeout_seconds,
                    },
                )

            # Check uptime
            uptime = datetime.now() - self._metrics.start_time
            if uptime < timedelta(seconds=10):
                return HealthCheck(
                    status=HealthStatus.DEGRADED,
                    message="Recently started",
                    timestamp=datetime.now(),
                    details={"uptime_seconds": uptime.total_seconds()},
                )

            return HealthCheck(
                status=HealthStatus.HEALTHY,
                message="Agent is healthy",
                timestamp=datetime.now(),
                details={
                    "uptime_seconds": uptime.total_seconds(),
                    "request_count": self._metrics.request_count,
                    "error_rate": (
                        (self._metrics.request_errors / self._metrics.request_count)
                        if self._metrics.request_count > 0
                        else 0
                    ),
                    "average_response_time": self._metrics.average_response_time,
                },
            )

        except Exception as e:
            self._monitor_logger.error(f"Health check failed: {e}")
            return HealthCheck(
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {e}",
                timestamp=datetime.now(),
            )

    async def get_health(self) -> HealthCheck:
        """Get current health status."""
        health_check = await self._perform_health_check()
        self._metrics.health_checks.append(health_check)

        # Keep only last 100 health checks
        if len(self._metrics.health_checks) > 100:
            self._metrics.health_checks = self._metrics.health_checks[-100:]

        return health_check

    def get_metrics(self) -> AgentMetrics:
        """Get agent metrics."""
        return self._metrics

    async def start(self) -> None:
        """Start agent with monitoring."""
        await super().start()
        self._monitor_logger.info(
            f"Monitored agent {self.config.name} started (attempt #{self._metrics.restart_count + 1})"
        )

    async def stop(self) -> None:
        """Stop agent with monitoring."""
        await super().stop()
        self._monitor_logger.info(
            f"Monitored agent {self.config.name} stopped after "
            f"{(datetime.now() - self._metrics.start_time).total_seconds():.1f} seconds"
        )

    async def restart(self) -> None:
        """Restart the agent."""
        self._monitor_logger.info(f"Restarting agent {self.config.name}")
        self._metrics.restart_count += 1

        # Stop if running
        if self.state in [AgentState.RUNNING, AgentState.STARTING]:
            await self.stop()

        # Reset state
        self.state = AgentState.INITIALIZED
        self._stop_event.clear()

        # Start again
        await self.start()


class MonitoringService:
    """Service for monitoring multiple agents."""

    def __init__(self):
        """Initialize monitoring service."""
        self.agents: Dict[str, MonitoredAgent] = {}
        self.logger = logging.getLogger("monitoring_service")

    def register_agent(self, agent: MonitoredAgent) -> None:
        """Register an agent for monitoring."""
        self.agents[agent.config.name] = agent
        self.logger.info(f"Registered agent {agent.config.name} for monitoring")

    def unregister_agent(self, agent_name: str) -> None:
        """Unregister an agent from monitoring."""
        if agent_name in self.agents:
            del self.agents[agent_name]
            self.logger.info(f"Unregistered agent {agent_name} from monitoring")

    async def check_all_health(self) -> Dict[str, HealthCheck]:
        """Check health of all registered agents."""
        health_results = {}

        for name, agent in self.agents.items():
            try:
                health_results[name] = await agent.get_health()
            except Exception as e:
                self.logger.error(f"Failed to check health of {name}: {e}")
                health_results[name] = HealthCheck(
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check failed: {e}",
                    timestamp=datetime.now(),
                )

        return health_results

    def get_all_metrics(self) -> Dict[str, AgentMetrics]:
        """Get metrics for all registered agents."""
        return {name: agent.get_metrics() for name, agent in self.agents.items()}

    async def restart_unhealthy_agents(self) -> List[str]:
        """Restart agents with unhealthy status."""
        restarted = []
        health_results = await self.check_all_health()

        for name, health in health_results.items():
            if health.status == HealthStatus.UNHEALTHY:
                self.logger.warning(f"Restarting unhealthy agent {name}")
                try:
                    await self.agents[name].restart()
                    restarted.append(name)
                except Exception as e:
                    self.logger.error(f"Failed to restart agent {name}: {e}")

        return restarted

    def generate_health_report(self) -> Dict[str, Any]:
        """Generate a comprehensive health report."""
        health_results = {}
        metrics = self.get_all_metrics()

        # Get latest health check for each agent
        for name, agent_metrics in metrics.items():
            if agent_metrics.health_checks:
                health_results[name] = agent_metrics.health_checks[-1]

        # Calculate summary statistics
        total_agents = len(self.agents)
        healthy_agents = sum(
            1
            for health in health_results.values()
            if health.status == HealthStatus.HEALTHY
        )
        degraded_agents = sum(
            1
            for health in health_results.values()
            if health.status == HealthStatus.DEGRADED
        )
        unhealthy_agents = sum(
            1
            for health in health_results.values()
            if health.status == HealthStatus.UNHEALTHY
        )

        return {
            "summary": {
                "total_agents": total_agents,
                "healthy_agents": healthy_agents,
                "degraded_agents": degraded_agents,
                "unhealthy_agents": unhealthy_agents,
                "health_percentage": (
                    (healthy_agents / total_agents * 100) if total_agents > 0 else 0
                ),
            },
            "agents": {
                name: {
                    "health": health_results.get(name),
                    "metrics": {
                        "uptime_seconds": (
                            datetime.now() - agent_metrics.start_time
                        ).total_seconds(),
                        "restart_count": agent_metrics.restart_count,
                        "error_count": agent_metrics.error_count,
                        "request_count": agent_metrics.request_count,
                        "request_errors": agent_metrics.request_errors,
                        "average_response_time": agent_metrics.average_response_time,
                        "last_error": agent_metrics.last_error,
                        "last_error_time": (
                            agent_metrics.last_error_time.isoformat()
                            if agent_metrics.last_error_time
                            else None
                        ),
                    },
                }
                for name, agent_metrics in metrics.items()
            },
            "generated_at": datetime.now().isoformat(),
        }
