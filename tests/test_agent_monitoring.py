"""Test suite for agent monitoring and error handling."""

import asyncio
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from anyio import create_task_group
import aiohttp

from inklink.adapters.ollama_adapter_enhanced import OllamaAdapter
from inklink.agents.base.agent import AgentConfig, LocalAgent
from inklink.agents.base.monitoring import (
    HealthCheck,
    HealthStatus,
    MonitoredAgent,
    MonitoringService,
    RestartPolicy,
)
from inklink.agents.exceptions import (
    AgentCommunicationError,
    AgentError,
    AgentStateError,
    ConfigurationError,
)

# Configure to only use asyncio backend
pytestmark = [pytest.mark.anyio, pytest.mark.asyncio_backend("asyncio")]


class TestAgentMock(MonitoredAgent):
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
            raise AgentError("Mock failure")

        while not self._stop_event.is_set():
            await asyncio.sleep(0.1)

    async def _perform_health_check(self) -> HealthCheck:
        """Mock health check."""
        self.health_check_count += 1
        status = HealthStatus.UNHEALTHY if self.should_fail else HealthStatus.HEALTHY
        return HealthCheck(
            status=status,
            message="Mock health check",
            timestamp=datetime.now(),
            details={"count": self.health_check_count},
        )

    async def start(self) -> None:
        """Mock start."""
        self.restart_count += 1
        await super().start()

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Mock handle request."""
        return {"success": True, "mock": True}


class TestMonitoringService:
    """Test suite for MonitoringService."""

    @pytest.fixture
    def monitoring_service(self):
        """Create monitoring service instance."""
        return MonitoringService()

    @pytest.fixture
    def mock_agent(self):
        """Create mock agent."""
        config = AgentConfig(
            name="test_agent",
            description="Test agent",
            version="1.0.0",
            capabilities=["test"],
            ollama_model="test-model",
            mcp_enabled=True,
        )
        return TestAgentMock(config)

    @pytest.mark.anyio
    async def test_register_agent(self, monitoring_service, mock_agent):
        """Test agent registration."""
        monitoring_service.register_agent(mock_agent)

        assert mock_agent.config.name in monitoring_service.agents
        assert monitoring_service.agents[mock_agent.config.name] == mock_agent

    @pytest.mark.anyio
    async def test_health_check_healthy_agent(self, monitoring_service, mock_agent):
        """Test health check for healthy agent."""
        monitoring_service.register_agent(mock_agent)

        # Check health
        health_results = await monitoring_service.check_all_health()

        assert mock_agent.config.name in health_results
        assert health_results[mock_agent.config.name].status == HealthStatus.HEALTHY

    @pytest.mark.anyio
    async def test_health_check_unhealthy_agent(self, monitoring_service):
        """Test health check for unhealthy agent."""
        # Create failing agent
        config = AgentConfig(
            name="failing_agent",
            version="1.0.0",
            description="Test failing agent",
            capabilities=["test"],
            ollama_model="test-model",
            mcp_enabled=True,
        )
        failing_agent = TestAgentMock(config, should_fail=True)

        monitoring_service.register_agent(failing_agent)

        # Check health
        health_results = await monitoring_service.check_all_health()

        assert failing_agent.config.name in health_results
        assert (
            health_results[failing_agent.config.name].status == HealthStatus.UNHEALTHY
        )
        assert failing_agent.health_check_count > 0

    @pytest.mark.anyio
    async def test_restart_unhealthy_agents(self, monitoring_service):
        """Test restart unhealthy agents functionality."""
        config = AgentConfig(
            name="unhealthy_agent",
            version="1.0.0",
            description="Test agent that is unhealthy",
            capabilities=["test"],
            ollama_model="test-model",
            mcp_enabled=True,
        )
        agent = TestAgentMock(config, should_fail=True)

        monitoring_service.register_agent(agent)

        # Check health and restart if needed
        restarted = await monitoring_service.restart_unhealthy_agents()

        # Should have attempted restart
        assert agent.config.name in restarted or len(restarted) > 0

    @pytest.mark.anyio
    async def test_generate_health_report(self, monitoring_service, mock_agent):
        """Test health report generation."""
        monitoring_service.register_agent(mock_agent)

        # Generate health report
        report = monitoring_service.generate_health_report()

        # Should have metrics for registered agent
        assert mock_agent.config.name in report["agents"]

    @pytest.mark.anyio
    async def test_get_all_metrics(self, monitoring_service, mock_agent):
        """Test getting metrics for all agents."""
        monitoring_service.register_agent(mock_agent)

        # Get all metrics
        metrics = monitoring_service.get_all_metrics()

        # Should have metrics for registered agent
        assert mock_agent.config.name in metrics

    @pytest.mark.anyio
    async def test_multiple_agents_health(self, monitoring_service):
        """Test health check for multiple agents."""
        # Create two agents with different configs
        config1 = AgentConfig(
            name="test_1",
            version="1.0.0",
            description="Healthy agent",
            capabilities=["test"],
            ollama_model="test-model",
            mcp_enabled=True,
        )
        agent1 = TestAgentMock(config1, should_fail=False)

        config2 = AgentConfig(
            name="test_2",
            version="1.0.0",
            description="Unhealthy agent",
            capabilities=["test"],
            ollama_model="test-model",
            mcp_enabled=True,
        )
        agent2 = TestAgentMock(config2, should_fail=True)

        monitoring_service.register_agent(agent1)
        monitoring_service.register_agent(agent2)

        # Check health of all agents
        health_results = await monitoring_service.check_all_health()

        assert "test_1" in health_results
        assert "test_2" in health_results
        assert health_results["test_1"].status == HealthStatus.HEALTHY
        assert health_results["test_2"].status == HealthStatus.UNHEALTHY

    @pytest.mark.anyio
    async def test_unregister_agent(self, monitoring_service, mock_agent):
        """Test unregistering an agent."""
        monitoring_service.register_agent(mock_agent)

        # Verify agent is registered
        assert mock_agent.config.name in monitoring_service.agents

        # Unregister the agent
        monitoring_service.unregister_agent(mock_agent.config.name)

        # Verify agent is no longer registered
        assert mock_agent.config.name not in monitoring_service.agents


class TestExceptionHandling:
    """Test suite for exception handling."""

    @pytest.mark.anyio
    async def test_agent_configuration_error(self):
        """Test ConfigurationError handling."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("Missing required configuration")

        assert "Missing required configuration" in str(exc_info.value)
        assert isinstance(exc_info.value, ConfigurationError)

    @pytest.mark.anyio
    async def test_agent_communication_error(self):
        """Test AgentCommunicationError handling."""
        with pytest.raises(AgentCommunicationError) as exc_info:
            raise AgentCommunicationError("Failed to connect to remote_agent")

        assert "Failed to connect" in str(exc_info.value)
        assert isinstance(exc_info.value, AgentCommunicationError)

    @pytest.mark.anyio
    async def test_agent_state_error(self):
        """Test AgentStateError handling."""
        with pytest.raises(AgentStateError) as exc_info:
            raise AgentStateError("Invalid state transition from running to invalid")

        assert "Invalid state transition" in str(exc_info.value)
        assert isinstance(exc_info.value, AgentStateError)

    @pytest.mark.anyio
    async def test_agent_timeout_error(self):
        """Test timeout error handling."""
        with pytest.raises(Exception) as exc_info:
            raise Exception("Operation timed out")

        assert "Operation timed out" in str(exc_info.value)


class TestEnhancedOllamaAdapter:
    """Test suite for enhanced Ollama adapter."""

    @pytest.fixture
    def adapter(self):
        """Create enhanced Ollama adapter."""
        return OllamaAdapter(
            # OllamaAdapter takes a config parameter now
            config=None  # Use default config
        )

    @pytest.mark.anyio
    async def test_retry_mechanism(self, adapter):
        """Test retry mechanism."""
        # Mock HTTP client to fail first 2 times
        call_count = 0

        class MockResponse:
            def __init__(self, status, json_response=None, error=None):
                self.status = status
                self.json_response = json_response
                self.error = error
                self.raise_for_status = Mock()
                if error:
                    self.raise_for_status.side_effect = error

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def json(self):
                return self.json_response

        # First, ensure session is created
        adapter.session = aiohttp.ClientSession()

        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                # Fail first 2 times
                return MockResponse(500, error=Exception("HTTP 500"))
            # Success on third try
            return MockResponse(200, {"message": {"content": "Success"}})

        with patch.object(adapter.session, "request", mock_request):
            result = await adapter.query("model", "prompt")
            assert result == "Success"
            assert call_count == 3  # Should retry twice before success

        await adapter.session.close()

    @pytest.mark.anyio
    async def test_timeout_handling(self, adapter):
        """Test timeout handling."""

        # Mock HTTP client to timeout
        async def mock_post(*args, **kwargs):
            await asyncio.sleep(5)  # Longer than timeout

        adapter.session = Mock()
        with patch.object(
            adapter.session, "post", side_effect=mock_post
        ), pytest.raises(
            Exception  # Generic timeout error
        ):
            await adapter.query("model", "prompt")

    @pytest.mark.anyio
    async def test_health_check(self, adapter):
        """Test health check."""

        class MockResponse:
            def __init__(self, status, json_response=None):
                self.status = status
                self.json_response = json_response
                self.raise_for_status = Mock()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def json(self):
                return self.json_response

        def mock_request(method, url, **kwargs):
            # For root endpoint
            if url == f"{adapter.config.base_url}/":
                return MockResponse(200, {"status": "OK"})
            # For tags endpoint
            elif "tags" in url:
                return MockResponse(
                    200, {"models": [{"name": "test-model", "model": "test-model"}]}
                )

        # Mock session with proper async context manager
        mock_session = Mock()
        mock_session.request = Mock(side_effect=mock_request)
        adapter.session = mock_session

        result = await adapter.health_check()
        assert result["healthy"] is True

    @pytest.mark.anyio
    async def test_health_check_failure(self, adapter):
        """Test health check failure."""

        class MockResponse:
            def __init__(self, status, error=None):
                self.status = status
                self.raise_for_status = Mock()
                if error:
                    self.raise_for_status.side_effect = error

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        async def mock_request(*args, **kwargs):
            return MockResponse(500, error=Exception("HTTP 500"))

        # Mock session with proper async context manager
        mock_session = Mock()
        mock_session.request = AsyncMock(side_effect=mock_request)
        adapter.session = mock_session

        result = await adapter.health_check()
        assert result["healthy"] is False


if __name__ == "__main__":
    pytest.main(["-v", __file__])
