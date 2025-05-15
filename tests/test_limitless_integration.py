"""Tests for Limitless Life Log integration.

This module tests the Limitless adapter, service, and scheduler.
"""
import os
import pytest
from unittest.mock import Mock

from inklink.adapters.limitless_adapter import LimitlessAdapter
from inklink.services.limitless_life_log_service import LimitlessLifeLogService
from inklink.services.limitless_scheduler_service import LimitlessSchedulerService


@pytest.fixture
def mock_response():
    """Mock HTTP response."""
    mock = Mock()
    mock.json.return_value = {"data": []}
    mock.raise_for_status.return_value = None
    return mock


@pytest.fixture
def mock_session(mock_response):
    """Mock requests session."""
    mock = Mock()
    mock.request.return_value = mock_response
    mock.get.return_value = mock_response
    mock.post.return_value = mock_response
    return mock


@pytest.fixture
def mock_http_adapter():
    """Mock HTTP adapter."""
    mock = Mock()
    mock.get.return_value = (True, {"data": [], "pagination": {}})
    return mock


@pytest.fixture
def limitless_adapter(mock_http_adapter):
    """Create Limitless adapter with mocked HTTP adapter."""
    adapter = LimitlessAdapter(api_key="mock_api_key")
    adapter.http_adapter = mock_http_adapter
    return adapter


@pytest.fixture
def mock_kg_service():
    """Mock knowledge graph service."""
    mock = Mock()
    mock.extract_entities.return_value = []
    mock.extract_relationships.return_value = []
    mock.add_entity.return_value = (True, "Entity added")
    mock.add_relationship.return_value = (True, "Relationship added")
    return mock


@pytest.fixture
def limitless_service(limitless_adapter, mock_kg_service, tmp_path):
    """Create Limitless service with mocked dependencies."""
    storage_path = str(tmp_path / "limitless")
    os.makedirs(storage_path, exist_ok=True)

    service = LimitlessLifeLogService(
        limitless_adapter=limitless_adapter,
        knowledge_graph_service=mock_kg_service,
        storage_path=storage_path,
    )
    return service


@pytest.fixture
def limitless_scheduler(limitless_service):
    """Create Limitless scheduler with mocked service."""
    scheduler = LimitlessSchedulerService(
        limitless_service=limitless_service,
        sync_interval=60,  # Use short interval for tests
        initial_delay=0,  # No delay for tests
    )
    return scheduler


def test_limitless_adapter_ping(limitless_adapter, mock_http_adapter):
    """Test Limitless adapter ping method."""
    # Test successful ping
    mock_http_adapter.get.return_value = (True, {"data": []})
    assert limitless_adapter.ping() is True

    # Test failed ping
    mock_http_adapter.get.return_value = (False, "Error")
    assert limitless_adapter.ping() is False


def test_limitless_adapter_get_life_logs(limitless_adapter, mock_http_adapter):
    """Test Limitless adapter get_life_logs method."""
    # Setup mock response
    life_logs = [
        {
            "id": "log1",
            "title": "Test log",
            "content": "This is a test log",
            "created_at": "2023-01-01T00:00:00Z",
        }
    ]
    mock_http_adapter.get.return_value = (
        True,
        {"data": life_logs, "pagination": {"next_cursor": None}},
    )

    # Call method
    success, result = limitless_adapter.get_life_logs()

    # Check results
    assert success is True
    assert "data" in result
    assert result["data"] == life_logs


def test_limitless_service_sync_logs(
    limitless_service, limitless_adapter, mock_kg_service, mock_http_adapter
):
    """Test Limitless service sync_life_logs method."""
    # Setup mock response
    life_logs = [
        {
            "id": "log1",
            "title": "Test log",
            "content": "This is a test log with entities and relationships",
            "created_at": "2023-01-01T00:00:00Z",
        }
    ]
    mock_http_adapter.get.return_value = (
        True,
        {"data": life_logs, "pagination": {"next_cursor": None}},
    )

    # Setup mock entity extraction
    mock_kg_service.extract_entities.return_value = [
        {"id": "entity1", "name": "Entity 1", "type": "Person"}
    ]
    mock_kg_service.extract_relationships.return_value = [
        {"from_id": "lifelog:log1", "to_id": "entity1", "type": "MENTIONS"}
    ]

    # Call method
    success, message = limitless_service.sync_life_logs()

    # Check results
    assert success is True
    assert "Successfully synced" in message

    # Verify knowledge graph service calls
    mock_kg_service.add_entity.assert_called()
    mock_kg_service.extract_entities.assert_called_with(life_logs[0]["content"])
    mock_kg_service.extract_relationships.assert_called_with(life_logs[0]["content"])


def test_limitless_scheduler(limitless_scheduler, limitless_service):
    """Test Limitless scheduler start/stop methods."""
    # Test start
    assert limitless_scheduler.start() is True
    assert limitless_scheduler.running is True

    # Test double start (should return False)
    assert limitless_scheduler.start() is False

    # Test stop
    assert limitless_scheduler.stop() is True
    assert limitless_scheduler.running is False

    # Test double stop (should return False)
    assert limitless_scheduler.stop() is False


def test_limitless_scheduler_trigger_sync(limitless_scheduler, limitless_service):
    """Test Limitless scheduler trigger_sync method."""
    # Mock service sync method
    limitless_service.sync_life_logs = Mock(return_value=(True, "Synced successfully"))

    # Call trigger_sync
    result = limitless_scheduler.trigger_sync()

    # Check results
    assert result["success"] is True
    assert "next_sync" in result

    # Verify service method called
    limitless_service.sync_life_logs.assert_called_once_with(force_full_sync=False)

    # Test force_full_sync
    limitless_scheduler.trigger_sync(force_full_sync=True)
    limitless_service.sync_life_logs.assert_called_with(force_full_sync=True)
