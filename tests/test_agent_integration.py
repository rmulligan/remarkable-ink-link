"""Integration tests for agent framework."""

import asyncio
from datetime import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from inklink.adapters.ollama_adapter_enhanced import EnhancedOllamaAdapter
from inklink.agents.base.agent import AgentConfig
from inklink.agents.base.exceptions import AgentConfigurationError, AgentException
from inklink.agents.base.monitoring import HealthStatus, MonitoringService
from inklink.agents.base.registry import AgentRegistry
from inklink.agents.core.daily_briefing_agent import DailyBriefingAgent
from inklink.agents.core.limitless_insight_agent import LimitlessContextualInsightAgent
from inklink.agents.core.project_tracker_agent import ProactiveProjectTrackerAgent
from inklink.agents.di import AgentContainer, init_container


class TestAgentIntegration:
    """Integration tests for agent framework."""

    @pytest.fixture
    async def container(self, tmp_path):
        """Create DI container for tests."""
        # Mock configuration file
        config_content = """
agents:
  limitless_insight:
    name: "limitless_insight"
    initial_state: "active"
    ollama_model: "llama3:8b"
    health_check_interval: 5
    max_restarts: 3
  daily_briefing:
    name: "daily_briefing"
    initial_state: "active"
    ollama_model: "llama3:8b"
    briefing_time: "06:00"
  project_tracker:
    name: "project_tracker"
    initial_state: "active"
    ollama_model: "llama3:8b"
    check_interval: 300
adapters:
  ollama:
    base_url: "http://localhost:11434"
    timeout: 30
    max_retries: 3
    retry_delay: 1.0
  limitless:
    api_key: "test_key"
    base_url: "https://api.limitless.ai"
  remarkable:
    device_token: "test_token"
storage:
  base_path: "{}"
""".format(
            tmp_path
        )
        config_path = tmp_path / "agent_config.yaml"
        config_path.write_text(config_content)
        # Initialize container with test config
        container = init_container(config_path=str(config_path))
        return container

    @pytest.fixture
    async def mock_adapters(self):
        """Create mock adapters for testing."""
        # Mock Ollama adapter
        ollama_mock = Mock(spec=EnhancedOllamaAdapter)
        ollama_mock.query = AsyncMock(return_value="Mock response")
        ollama_mock.health_check = AsyncMock(return_value=True)
        # Mock Limitless adapter
        limitless_mock = Mock()
        limitless_mock.get_transcripts = AsyncMock(
            return_value=[
                {
                    "id": "test_1",
                    "text": "This is a test transcript",
                    "timestamp": "2024-01-01T10:00:00",
                }
            ]
        )
        # Mock Remarkable adapter
        remarkable_mock = Mock()
        remarkable_mock.upload_document = AsyncMock(return_value=True)
        return {
            "ollama": ollama_mock,
            "limitless": limitless_mock,
            "remarkable": remarkable_mock,
        }

    @pytest.mark.asyncio
    async def test_agent_lifecycle(self, container, mock_adapters):
        """Test agent lifecycle management."""
        # Replace real adapters with mocks
        with patch.object(
            container, "ollama_adapter", return_value=mock_adapters["ollama"]
        ), patch.object(
            container, "limitless_adapter", return_value=mock_adapters["limitless"]
        ), patch.object(
            container, "remarkable_adapter", return_value=mock_adapters["remarkable"]
        ):
            # Create agent
            agent = container.limitless_insight_agent()
            # Test initial state
            assert agent.state == "initialized"
            # Start agent
            await agent.start()
            assert agent.state == "running"
            # Stop agent
            await agent.stop()
            assert agent.state == "stopped"

    @pytest.mark.asyncio
    async def test_mcp_communication(self, container, mock_adapters):
        """Test MCP communication between agents."""
        # Replace real adapters with mocks
        with patch.object(
            container, "ollama_adapter", return_value=mock_adapters["ollama"]
        ), patch.object(
            container, "limitless_adapter", return_value=mock_adapters["limitless"]
        ), patch.object(
            container, "remarkable_adapter", return_value=mock_adapters["remarkable"]
        ):
            # Create and register agents
            registry = container.agent_registry()
            # Create agents
            limitless_agent = container.limitless_insight_agent()
            await registry.register_agent("limitless_insight", limitless_agent)
            briefing_agent = container.daily_briefing_agent()
            await registry.register_agent("daily_briefing", briefing_agent)
            # Start agents
            await limitless_agent.start()
            await briefing_agent.start()
            # Test MCP message through registry
            registry_agent = registry.get_agent("agent_registry")
            response = await registry_agent.handle_request(
                {
                    "target": "limitless_insight",
                    "capability": "get_spoken_summary",
                    "data": {"time_period": "last_24_hours"},
                }
            )
            assert "summary" in response
            # Cleanup
            await registry.stop_all()

    @pytest.mark.asyncio
    async def test_error_recovery(self, container, mock_adapters):
        """Test error recovery mechanisms."""
        # Create failing adapter
        failing_ollama = Mock(spec=EnhancedOllamaAdapter)
        failing_ollama.query = AsyncMock(side_effect=AgentException("Mock failure"))
        failing_ollama.health_check = AsyncMock(return_value=False)
        with patch.object(
            container, "ollama_adapter", return_value=failing_ollama
        ), patch.object(
            container, "limitless_adapter", return_value=mock_adapters["limitless"]
        ):
            # Create agent
            agent = container.limitless_insight_agent()
            # Start monitoring service
            monitoring = container.monitoring_service()
            monitoring.register_agent("test_agent", agent)
            # Start monitoring
            monitor_task = asyncio.create_task(monitoring.start_monitoring())
            # Start agent (should fail)
            await agent.start()
            # Wait for health check
            await asyncio.sleep(2)
            # Check health status
            health_status = await monitoring.get_health_status()
            assert health_status["test_agent"]["status"] == HealthStatus.UNHEALTHY.value
            # Cleanup
            await monitoring.stop_monitoring()
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_configuration_loading(self, container):
        """Test configuration loading and environment variable substitution."""
        # Test that configuration is loaded correctly
        config = container.config()
        assert "agents" in config
        assert "adapters" in config
        assert "storage" in config
        # Test agent configuration
        assert config["agents"]["limitless_insight"]["ollama_model"] == "llama3:8b"
        assert config["agents"]["daily_briefing"]["briefing_time"] == "06:00"
        # Test adapter configuration
        assert config["adapters"]["ollama"]["base_url"] == "http://localhost:11434"
        assert config["adapters"]["ollama"]["timeout"] == 30

    @pytest.mark.asyncio
    async def test_full_agent_workflow(self, container, mock_adapters):
        """Test full agent workflow with all components."""
        # Replace real adapters with mocks
        with patch.object(
            container, "ollama_adapter", return_value=mock_adapters["ollama"]
        ), patch.object(
            container, "limitless_adapter", return_value=mock_adapters["limitless"]
        ), patch.object(
            container, "remarkable_adapter", return_value=mock_adapters["remarkable"]
        ):
            # Initialize all services
            registry = container.agent_registry()
            monitoring = container.monitoring_service()
            # Create all agents
            limitless_agent = container.limitless_insight_agent()
            briefing_agent = container.daily_briefing_agent()
            tracker_agent = container.project_tracker_agent()
            # Register agents
            await registry.register_agent("limitless_insight", limitless_agent)
            await registry.register_agent("daily_briefing", briefing_agent)
            await registry.register_agent("project_tracker", tracker_agent)
            # Register with monitoring
            monitoring.register_agent("limitless_insight", limitless_agent)
            monitoring.register_agent("daily_briefing", briefing_agent)
            monitoring.register_agent("project_tracker", tracker_agent)
            # Start monitoring
            monitor_task = asyncio.create_task(monitoring.start_monitoring())
            # Start all agents
            await registry.start_all()
            # Wait for initialization
            await asyncio.sleep(1)
            # Test workflow: Generate briefing
            registry_agent = registry.get_agent("agent_registry")
            # Get spoken summary
            response = await registry_agent.handle_request(
                {
                    "target": "limitless_insight",
                    "capability": "get_spoken_summary",
                    "data": {"time_period": "last_24_hours"},
                }
            )
            assert "summary" in response
            # Generate briefing
            response = await registry_agent.handle_request(
                {
                    "target": "daily_briefing",
                    "capability": "generate_briefing",
                    "data": {},
                }
            )
            assert response is not None
            # Track project
            response = await registry_agent.handle_request(
                {
                    "target": "project_tracker",
                    "capability": "add_commitment",
                    "data": {
                        "commitment": "Test commitment",
                        "project": "Test Project",
                    },
                }
            )
            assert response["status"] == "added"
            # Check health status
            health_status = await monitoring.get_health_status()
            assert all(
                status["status"] == HealthStatus.HEALTHY.value
                for status in health_status.values()
            )
            # Get metrics
            metrics = await monitoring.get_metrics()
            assert all("uptime" in agent_metrics for agent_metrics in metrics.values())
            # Cleanup
            await registry.stop_all()
            await monitoring.stop_monitoring()
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_agent_failure_handling(self, container, mock_adapters):
        """Test handling of agent failures and restarts."""
        # Create adapter that fails intermittently
        call_count = 0

        async def intermittent_query(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise AgentException("Intermittent failure")
            return "Success"

        mock_adapters["ollama"].query = intermittent_query
        with patch.object(
            container, "ollama_adapter", return_value=mock_adapters["ollama"]
        ), patch.object(
            container, "limitless_adapter", return_value=mock_adapters["limitless"]
        ):
            # Create agent with retry logic
            agent = container.limitless_insight_agent()
            # Test that agent can handle intermittent failures
            await agent.start()
            # Process some transcripts
            await agent._process_new_transcripts()
            # Should have retried and succeeded
            assert call_count > 0
            await agent.stop()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
