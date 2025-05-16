"""Test suite for agent monitoring and error handling."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from inklink.adapters.ollama_adapter_enhanced import EnhancedOllamaAdapter
from inklink.agents.base.agent import AgentConfig, LocalAgent
from inklink.agents.base.exceptions import (
    AgentCommunicationError,
    AgentConfigurationError,
    AgentException,
    AgentStateError,
    AgentTimeoutError,
)
from inklink.agents.base.monitoring import (
    HealthStatus,
    MonitoringService,
    RestartPolicy,
)


class TestAgentMock(LocalAgent):
    """Mock agent for testing."""

    def __init__(self, config: AgentConfig, should_fail: bool = False):
        super().__init__(config)
        self.should_fail = should_fail
        self.health_check_count = 0
        self.restart_count = 0

    async def _agent_logic(self) -> None:
        """Mock agent logic."""
        if self.should_fail:
            await asyncio.sleep(0.1)
            raise AgentException("Mock failure")

        while not self._stop_event.is_set():
            await asyncio.sleep(0.1)

    async def health_check(self) -> HealthStatus:
        """Mock health check."""
        self.health_check_count += 1
        if self.should_fail:
            return HealthStatus.UNHEALTHY
        return HealthStatus.HEALTHY

    async def start(self) -> None:
        """Mock start."""
        self.restart_count += 1
        await super().start()


class TestMonitoringService:
    """Test suite for MonitoringService."""

    @pytest.fixture
    def monitoring_service(self):
        """Create monitoring service instance."""
        return MonitoringService(check_interval=0.5)  # Fast checks for tests

    @pytest.fixture
    def mock_agent(self):
        """Create mock agent."""
        config = AgentConfig(
            name="test_agent",
            initial_state="active",
            health_check_interval=0.5,
            restart_policy=RestartPolicy.ALWAYS,
        )
        return TestAgentMock(config)

    @pytest.mark.asyncio
    async def test_register_agent(self, monitoring_service, mock_agent):
        """Test agent registration."""
        monitoring_service.register_agent("test_1", mock_agent)

        assert "test_1" in monitoring_service._agents
        assert monitoring_service._agents["test_1"] == mock_agent
        assert "test_1" in monitoring_service._health_status
        assert monitoring_service._health_status["test_1"] == HealthStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_health_check_healthy_agent(self, monitoring_service, mock_agent):
        """Test health check for healthy agent."""
        monitoring_service.register_agent("test_1", mock_agent)

        # Start monitoring
        monitoring_task = asyncio.create_task(monitoring_service.start_monitoring())

        # Wait for health check
        await asyncio.sleep(1)

        # Check health status
        assert monitoring_service._health_status["test_1"] == HealthStatus.HEALTHY
        assert mock_agent.health_check_count > 0

        # Stop monitoring
        await monitoring_service.stop_monitoring()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_agent(self, monitoring_service):
        """Test health check for unhealthy agent."""
        # Create failing agent
        config = AgentConfig(
            name="failing_agent",
            initial_state="active",
            health_check_interval=0.5,
            restart_policy=RestartPolicy.ON_FAILURE,
            max_restarts=2,
        )
        failing_agent = TestAgentMock(config, should_fail=True)

        monitoring_service.register_agent("test_1", failing_agent)

        # Start monitoring
        monitoring_task = asyncio.create_task(monitoring_service.start_monitoring())

        # Wait for health checks and restarts
        await asyncio.sleep(2)

        # Check health status
        assert monitoring_service._health_status["test_1"] == HealthStatus.UNHEALTHY
        assert failing_agent.health_check_count > 0
        assert failing_agent.restart_count <= config.max_restarts + 1

        # Stop monitoring
        await monitoring_service.stop_monitoring()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_restart_policy_always(self, monitoring_service):
        """Test ALWAYS restart policy."""
        config = AgentConfig(
            name="always_restart",
            initial_state="active",
            health_check_interval=0.5,
            restart_policy=RestartPolicy.ALWAYS,
            max_restarts=3,
        )
        agent = TestAgentMock(config, should_fail=True)

        monitoring_service.register_agent("test_1", agent)

        # Start monitoring
        monitoring_task = asyncio.create_task(monitoring_service.start_monitoring())

        # Wait for restarts
        await asyncio.sleep(3)

        # Should restart up to max_restarts
        assert agent.restart_count > 1
        assert agent.restart_count <= config.max_restarts + 1

        # Stop monitoring
        await monitoring_service.stop_monitoring()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_restart_policy_on_failure(self, monitoring_service):
        """Test ON_FAILURE restart policy."""
        config = AgentConfig(
            name="on_failure_restart",
            initial_state="active",
            health_check_interval=0.5,
            restart_policy=RestartPolicy.ON_FAILURE,
            max_restarts=2,
        )
        agent = TestAgentMock(config, should_fail=True)

        monitoring_service.register_agent("test_1", agent)

        # Start monitoring
        monitoring_task = asyncio.create_task(monitoring_service.start_monitoring())

        # Wait for restarts
        await asyncio.sleep(2)

        # Should restart on failure
        assert agent.restart_count > 0
        assert agent.restart_count <= config.max_restarts + 1

        # Stop monitoring
        await monitoring_service.stop_monitoring()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_restart_policy_never(self, monitoring_service):
        """Test NEVER restart policy."""
        config = AgentConfig(
            name="never_restart",
            initial_state="active",
            health_check_interval=0.5,
            restart_policy=RestartPolicy.NEVER,
        )
        agent = TestAgentMock(config, should_fail=True)

        monitoring_service.register_agent("test_1", agent)

        # Start monitoring
        monitoring_task = asyncio.create_task(monitoring_service.start_monitoring())

        # Wait for health check
        await asyncio.sleep(2)

        # Should not restart
        assert agent.restart_count == 0

        # Stop monitoring
        await monitoring_service.stop_monitoring()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_get_health_status(self, monitoring_service, mock_agent):
        """Test getting health status."""
        monitoring_service.register_agent("test_1", mock_agent)
        monitoring_service.register_agent(
            "test_2",
            TestAgentMock(
                AgentConfig(name="test_2", initial_state="active"), should_fail=True
            ),
        )

        # Start monitoring
        monitoring_task = asyncio.create_task(monitoring_service.start_monitoring())

        # Wait for health checks
        await asyncio.sleep(1)

        # Get health status
        health_status = await monitoring_service.get_health_status()

        assert "test_1" in health_status
        assert "test_2" in health_status
        assert health_status["test_1"]["status"] == HealthStatus.HEALTHY.value
        assert health_status["test_2"]["status"] == HealthStatus.UNHEALTHY.value

        # Stop monitoring
        await monitoring_service.stop_monitoring()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_get_metrics(self, monitoring_service, mock_agent):
        """Test getting metrics."""
        monitoring_service.register_agent("test_1", mock_agent)

        # Start monitoring
        monitoring_task = asyncio.create_task(monitoring_service.start_monitoring())

        # Simulate some activity
        monitoring_service._metrics["test_1"]["requests"] = 10
        monitoring_service._metrics["test_1"]["errors"] = 2
        monitoring_service._restart_counts["test_1"] = 1

        # Get metrics
        metrics = await monitoring_service.get_metrics()

        assert "test_1" in metrics
        assert metrics["test_1"]["requests"] == 10
        assert metrics["test_1"]["errors"] == 2
        assert metrics["test_1"]["restarts"] == 1
        assert metrics["test_1"]["uptime"] > 0

        # Stop monitoring
        await monitoring_service.stop_monitoring()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass


class TestExceptionHandling:
    """Test suite for exception handling."""

    @pytest.mark.asyncio
    async def test_agent_configuration_error(self):
        """Test AgentConfigurationError handling."""
        with pytest.raises(AgentConfigurationError) as exc_info:
            raise AgentConfigurationError("Missing required configuration")

        assert "Missing required configuration" in str(exc_info.value)
        assert isinstance(exc_info.value, AgentException)

    @pytest.mark.asyncio
    async def test_agent_communication_error(self):
        """Test AgentCommunicationError handling."""
        with pytest.raises(AgentCommunicationError) as exc_info:
            raise AgentCommunicationError("Failed to connect", target="remote_agent")

        assert "Failed to connect" in str(exc_info.value)
        assert exc_info.value.target == "remote_agent"

    @pytest.mark.asyncio
    async def test_agent_state_error(self):
        """Test AgentStateError handling."""
        with pytest.raises(AgentStateError) as exc_info:
            raise AgentStateError(
                "Invalid state transition",
                current_state="running",
                target_state="invalid",
            )

        assert "Invalid state transition" in str(exc_info.value)
        assert exc_info.value.current_state == "running"
        assert exc_info.value.target_state == "invalid"

    @pytest.mark.asyncio
    async def test_agent_timeout_error(self):
        """Test AgentTimeoutError handling."""
        with pytest.raises(AgentTimeoutError) as exc_info:
            raise AgentTimeoutError("Operation timed out", timeout=30)

        assert "Operation timed out" in str(exc_info.value)
        assert exc_info.value.timeout == 30


class TestEnhancedOllamaAdapter:
    """Test suite for enhanced Ollama adapter."""

    @pytest.fixture
    def adapter(self):
        """Create enhanced Ollama adapter."""
        return EnhancedOllamaAdapter(
            base_url="http://localhost:11434",
            timeout=30,
            max_retries=3,
            retry_delay=1.0,
        )

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, adapter):
        """Test retry mechanism."""
        # Mock HTTP client to fail first 2 times
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                response = Mock()
                response.status = 500
                response.text = AsyncMock(return_value="Server error")
                response.raise_for_status.side_effect = Exception("HTTP 500")
                return response
            # Success on third try
            response = Mock()
            response.status = 200
            response.json = AsyncMock(return_value={"response": "Success"})
            response.raise_for_status = Mock()
            return response

        # Patch the HTTP client
        with patch.object(adapter.client, "post", side_effect=mock_post):
            result = await adapter.query("model", "prompt")

            assert result == "Success"
            assert call_count == 3  # Should retry twice before success

    @pytest.mark.asyncio
    async def test_timeout_handling(self, adapter):
        """Test timeout handling."""

        # Mock HTTP client to timeout
        async def mock_post(*args, **kwargs):
            await asyncio.sleep(5)  # Longer than timeout

        with patch.object(adapter.client, "post", side_effect=mock_post), pytest.raises(
            AgentTimeoutError
        ):
            await adapter.query("model", "prompt")

    @pytest.mark.asyncio
    async def test_health_check(self, adapter):
        """Test health check."""

        # Mock successful response
        async def mock_get(*args, **kwargs):
            response = Mock()
            response.status = 200
            response.json = AsyncMock(return_value={"status": "ok"})
            response.raise_for_status = Mock()
            return response

        with patch.object(adapter.client, "get", side_effect=mock_get):
            result = await adapter.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, adapter):
        """Test health check failure."""

        # Mock failed response
        async def mock_get(*args, **kwargs):
            response = Mock()
            response.status = 500
            response.raise_for_status.side_effect = Exception("HTTP 500")
            return response

        with patch.object(adapter.client, "get", side_effect=mock_get):
            result = await adapter.health_check()
            assert result is False


if __name__ == "__main__":
    pytest.main(["-v", __file__])
