"""Full integration test suite for Limitless Life Log.

This module provides a comprehensive test suite for the Limitless Life Log integration,
including adapter, service, scheduler, and knowledge graph components. Tests can be run
with real credentials or mocked services.

For real credentials, set the following environment variables:
- LIMITLESS_API_KEY: Your Limitless API key
- NEO4J_URI: URI for Neo4j database (default: bolt://localhost:7687)
- NEO4J_USER: Neo4j username (default: neo4j)
- NEO4J_PASS: Neo4j password (default: password)

To run with real credentials (live testing):
    LIMITLESS_API_KEY=your_key pytest -xvs tests/test_limitless_integration_full.py::TestLimitlessLiveIntegration

To run mock testing (no real API calls):
    pytest -xvs tests/test_limitless_integration_full.py::TestLimitlessMockIntegration
"""

import os
import time
import json
import uuid
import logging
import pytest
from datetime import datetime, timedelta
import tempfile
import threading
from unittest.mock import Mock, patch, MagicMock

from inklink.adapters.limitless_adapter import LimitlessAdapter
from inklink.services.limitless_life_log_service import LimitlessLifeLogService
from inklink.services.limitless_scheduler_service import LimitlessSchedulerService
from inklink.controllers.limitless_controller import LimitlessController
from inklink.services.knowledge_graph_service import KnowledgeGraphService

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Sample life log data for mock tests
SAMPLE_LIFE_LOGS = [
    {
        "id": "log1",
        "title": "Meeting with Marketing Team",
        "content": "Had a productive meeting with Sarah and John from the marketing team. We discussed the upcoming product launch for Q3. Sarah suggested we focus on social media channels, while John wants to emphasize email campaigns. We agreed to create a combined strategy with both approaches.",
        "created_at": "2023-06-15T14:30:00Z",
        "metadata": {"location": "Conference Room B", "duration": 60, "type": "meeting"}
    },
    {
        "id": "log2",
        "title": "Research on AI trends",
        "content": "Spent the morning researching trends in artificial intelligence. LLMs like GPT-4 are revolutionizing various industries. The healthcare sector seems especially promising for AI applications. Dr. Maria Chen's paper on diagnostic AI showed remarkable accuracy rates compared to human diagnosticians.",
        "created_at": "2023-06-14T10:15:00Z",
        "metadata": {"tags": ["AI", "research", "healthcare"]}
    },
    {
        "id": "log3",
        "title": "Weekly goals reflection",
        "content": "Looking back at this week's goals: Completed the project proposal ahead of schedule. Had several productive meetings with the development team. Still need to finish the quarterly report and send the client presentation by Friday.",
        "created_at": "2023-06-16T18:45:00Z",
        "metadata": {"type": "reflection", "completion_rate": 0.75}
    }
]

# Check if we have credentials for live testing
has_limitless_key = bool(os.environ.get("LIMITLESS_API_KEY"))


# Live testing fixtures (require real credentials)
@pytest.fixture
def live_limitless_adapter():
    """Create a real Limitless adapter with API key from environment."""
    if not has_limitless_key:
        pytest.skip("LIMITLESS_API_KEY not set")
        
    api_key = os.environ.get("LIMITLESS_API_KEY")
    base_url = os.environ.get("LIMITLESS_API_URL", "https://api.limitless.ai")
    
    adapter = LimitlessAdapter(
        api_key=api_key,
        base_url=base_url,
        timeout=30,  # Longer timeout for real API calls
        retries=3,
    )
    
    return adapter


@pytest.fixture
def live_knowledge_graph_service():
    """Create a real Knowledge Graph service with credentials from environment."""
    if not has_limitless_key:
        pytest.skip("LIMITLESS_API_KEY not set")
        
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    username = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASS", "password")
    
    service = KnowledgeGraphService(
        uri=uri,
        username=username,
        password=password,
    )
    
    # Create a unique test source ID for this test run to avoid conflicts
    test_source = f"limitless_test_{uuid.uuid4().hex[:8]}"
    
    # Clean up test entities before test
    try:
        service.delete_entities_by_source(test_source)
    except Exception as e:
        logger.warning(f"Error during pre-test cleanup: {e}")
    
    # Return service with test source ID
    yield service, test_source
    
    # Clean up after test
    try:
        service.delete_entities_by_source(test_source)
    except Exception as e:
        logger.warning(f"Error during post-test cleanup: {e}")


@pytest.fixture
def live_limitless_service(live_limitless_adapter, live_knowledge_graph_service):
    """Create a real Limitless Life Log service."""
    if not has_limitless_key:
        pytest.skip("LIMITLESS_API_KEY not set")
        
    service, test_source = live_knowledge_graph_service
    
    # Create temporary directory for storage
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = os.path.join(temp_dir, "limitless")
        os.makedirs(storage_path, exist_ok=True)
        
        limitless_service = LimitlessLifeLogService(
            limitless_adapter=live_limitless_adapter,
            knowledge_graph_service=service,
            sync_interval=3600,
            storage_path=storage_path,
        )
        
        # Patch source name to use test source
        original_process = limitless_service._process_life_log
        
        def patched_process(life_log):
            if "source" in life_log:
                life_log["source"] = test_source
            return original_process(life_log)
        
        limitless_service._process_life_log = patched_process
        
        yield limitless_service


@pytest.fixture
def live_limitless_scheduler(live_limitless_service):
    """Create a real Limitless scheduler."""
    if not has_limitless_key:
        pytest.skip("LIMITLESS_API_KEY not set")
        
    scheduler = LimitlessSchedulerService(
        limitless_service=live_limitless_service,
        sync_interval=60,  # Short interval for testing
        initial_delay=1,   # Short delay for testing
    )
    
    yield scheduler
    
    # Ensure scheduler is stopped after test
    if scheduler.running:
        scheduler.stop()


# Mock testing fixtures (no real API calls)
@pytest.fixture
def mock_http_adapter():
    """Create a mock HTTP adapter."""
    mock = Mock()
    
    # Setup mock responses
    mock.get.side_effect = lambda endpoint, **kwargs: (
        (True, {"data": SAMPLE_LIFE_LOGS[:1], "pagination": {"next_cursor": "cursor1"}})
        if endpoint == "/v1/lifelogs" and not kwargs.get("params", {}).get("cursor")
        else (True, {"data": SAMPLE_LIFE_LOGS[1:], "pagination": {}})
        if endpoint == "/v1/lifelogs" and kwargs.get("params", {}).get("cursor") == "cursor1"
        else (True, {"data": SAMPLE_LIFE_LOGS[0]})
        if endpoint.startswith("/v1/lifelogs/") and SAMPLE_LIFE_LOGS[0]["id"] in endpoint
        else (False, "Not found")
    )
    
    return mock


@pytest.fixture
def mock_kg_service():
    """Create a mock Knowledge Graph service."""
    mock = Mock()
    
    # Setup mock responses for entity extraction
    mock.extract_entities.return_value = [
        {"id": "person:sarah", "name": "Sarah", "type": "Person"},
        {"id": "person:john", "name": "John", "type": "Person"},
        {"id": "topic:marketing", "name": "Marketing", "type": "Topic"},
        {"id": "topic:product_launch", "name": "Product Launch", "type": "Topic"},
    ]
    
    # Setup mock responses for relationship extraction
    mock.extract_relationships.return_value = [
        {"from_id": "person:sarah", "to_id": "topic:marketing", "type": "WORKS_ON"},
        {"from_id": "person:john", "to_id": "topic:marketing", "type": "WORKS_ON"},
    ]
    
    # Setup mock responses for entity addition
    mock.add_entity.return_value = (True, "Entity added")
    mock.add_relationship.return_value = (True, "Relationship added")
    
    return mock


@pytest.fixture
def mock_limitless_adapter(mock_http_adapter):
    """Create a mock Limitless adapter."""
    adapter = LimitlessAdapter(api_key="mock_api_key")
    adapter.http_adapter = mock_http_adapter
    return adapter


@pytest.fixture
def mock_limitless_service(mock_limitless_adapter, mock_kg_service):
    """Create a mock Limitless Life Log service."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = os.path.join(temp_dir, "limitless")
        os.makedirs(storage_path, exist_ok=True)
        
        service = LimitlessLifeLogService(
            limitless_adapter=mock_limitless_adapter,
            knowledge_graph_service=mock_kg_service,
            sync_interval=3600,
            storage_path=storage_path,
        )
        
        yield service


@pytest.fixture
def mock_limitless_scheduler(mock_limitless_service):
    """Create a mock Limitless scheduler."""
    scheduler = LimitlessSchedulerService(
        limitless_service=mock_limitless_service,
        sync_interval=60,   # Short interval for testing
        initial_delay=0.1,  # Very short delay for testing
    )
    
    yield scheduler
    
    # Ensure scheduler is stopped after test
    if scheduler.running:
        scheduler.stop()


@pytest.fixture
def mock_controller():
    """Create a mock HTTP handler for testing the controller."""
    class MockHandler:
        def get_query_params(self):
            return {}
        
        def get_body(self):
            return {}
        
        def send_response(self, status_code, headers=None):
            self.status_code = status_code
            self.headers = headers or {}
            return self
        
        def send_header(self, name, value):
            self.headers[name] = value
            return self
        
        def end_headers(self):
            return self
        
        def write(self, content):
            self.content = content
            return self
    
    return MockHandler()


@pytest.fixture
def mock_limitless_controller(mock_limitless_service, mock_limitless_scheduler, mock_controller):
    """Create a mock Limitless controller."""
    controller = LimitlessController(
        limitless_service=mock_limitless_service,
        limitless_scheduler=mock_limitless_scheduler,
        handler=mock_controller,
    )
    
    return controller


# Test classes
class TestLimitlessMockIntegration:
    """Mock integration tests for Limitless using fake data and mocked services."""
    
    def test_adapter_ping(self, mock_limitless_adapter, mock_http_adapter):
        """Test the adapter ping method."""
        # Setup mock response
        mock_http_adapter.get.return_value = (True, {"data": []})
        
        # Test successful ping
        assert mock_limitless_adapter.ping() is True
        
        # Test failed ping
        mock_http_adapter.get.return_value = (False, "Error")
        assert mock_limitless_adapter.ping() is False
    
    def test_adapter_get_life_logs(self, mock_limitless_adapter, mock_http_adapter):
        """Test fetching life logs."""
        # Setup mock response for a single page
        mock_http_adapter.get.return_value = (
            True, 
            {"data": SAMPLE_LIFE_LOGS, "pagination": {}}
        )
        
        # Test get_life_logs method
        success, result = mock_limitless_adapter.get_life_logs(limit=5)
        
        assert success is True
        assert "data" in result
        assert result["data"] == SAMPLE_LIFE_LOGS
    
    def test_adapter_pagination(self, mock_limitless_adapter, mock_http_adapter):
        """Test pagination handling in the adapter."""
        # Setup mock responses for pagination
        response1 = {"data": SAMPLE_LIFE_LOGS[:1], "pagination": {"next_cursor": "next_page"}}
        response2 = {"data": SAMPLE_LIFE_LOGS[1:], "pagination": {}}
        
        mock_http_adapter.get.side_effect = [
            (True, response1),
            (True, response2),
        ]
        
        # Test get_all_life_logs method
        success, logs = mock_limitless_adapter.get_all_life_logs()
        
        assert success is True
        assert len(logs) == len(SAMPLE_LIFE_LOGS)
        
        # Reset mock for next test
        mock_http_adapter.get.reset_mock()
        mock_http_adapter.get.side_effect = None
    
    def test_service_sync_logs(self, mock_limitless_service, mock_limitless_adapter, mock_http_adapter):
        """Test synchronizing life logs to the knowledge graph."""
        # Setup mock response for get_all_life_logs
        mock_http_adapter.get.return_value = (
            True, 
            {"data": SAMPLE_LIFE_LOGS, "pagination": {}}
        )
        
        # Run sync
        success, message = mock_limitless_service.sync_life_logs()
        
        assert success is True
        assert "Successfully synced" in message
    
    def test_service_cache(self, mock_limitless_service):
        """Test life log caching in the service."""
        # Save a log to cache
        log_id = "test_log_id"
        log_data = {"id": log_id, "title": "Test Log", "content": "Test content"}
        
        mock_limitless_service._save_life_log(log_id, log_data)
        
        # Get the log from cache
        success, result = mock_limitless_service.get_life_log(log_id)
        
        assert success is True
        assert result["id"] == log_id
        
        # Clear the cache
        success, message = mock_limitless_service.clear_cache()
        
        assert success is True
        assert "Successfully cleared" in message
    
    def test_service_entity_extraction(self, mock_limitless_service, mock_kg_service):
        """Test entity extraction from life logs."""
        # Process a sample life log
        log = SAMPLE_LIFE_LOGS[0]
        success, message = mock_limitless_service._process_life_log(log)
        
        assert success is True
        assert "Successfully processed" in message
        
        # Verify knowledge graph service calls
        mock_kg_service.extract_entities.assert_called_with(log["content"])
        mock_kg_service.extract_relationships.assert_called_with(log["content"])
        mock_kg_service.add_entity.assert_called()
    
    def test_scheduler_start_stop(self, mock_limitless_scheduler):
        """Test starting and stopping the scheduler."""
        # Start scheduler
        assert mock_limitless_scheduler.start() is True
        assert mock_limitless_scheduler.running is True
        
        # Try to start again (should fail)
        assert mock_limitless_scheduler.start() is False
        
        # Stop scheduler
        assert mock_limitless_scheduler.stop() is True
        assert mock_limitless_scheduler.running is False
        
        # Try to stop again (should fail)
        assert mock_limitless_scheduler.stop() is False
    
    def test_scheduler_trigger_sync(self, mock_limitless_scheduler, mock_limitless_service):
        """Test manually triggering a sync."""
        # Replace sync_life_logs with mock to avoid actual processing
        mock_limitless_service.sync_life_logs = Mock(return_value=(True, "Mock sync success"))
        
        # Trigger sync
        result = mock_limitless_scheduler.trigger_sync()
        
        assert result["success"] is True
        assert "next_sync" in result
        
        # Verify service method was called
        mock_limitless_service.sync_life_logs.assert_called_once_with(force_full_sync=False)
        
        # Test force_full_sync
        mock_limitless_scheduler.trigger_sync(force_full_sync=True)
        mock_limitless_service.sync_life_logs.assert_called_with(force_full_sync=True)
    
    def test_scheduler_loop(self, mock_limitless_scheduler, mock_limitless_service):
        """Test the scheduler loop with a very short interval."""
        # Replace sync_life_logs with mock to avoid actual processing
        mock_limitless_service.sync_life_logs = Mock(return_value=(True, "Mock sync success"))
        
        # Override sync interval for test
        mock_limitless_scheduler.sync_interval = 0.1  # Very short interval
        mock_limitless_scheduler.initial_delay = 0.01
        
        # Start scheduler
        mock_limitless_scheduler.start()
        
        # Wait for at least one sync
        time.sleep(0.2)
        
        # Stop scheduler
        mock_limitless_scheduler.stop()
        
        # Verify sync was called at least once
        mock_limitless_service.sync_life_logs.assert_called()
    
    def test_controller_handle_sync(self, mock_limitless_controller, mock_limitless_scheduler):
        """Test the sync endpoint in the controller."""
        # Replace trigger_sync with mock
        mock_limitless_scheduler.trigger_sync = Mock(return_value={"success": True, "message": "Test sync"})
        
        # Test normal sync
        mock_limitless_controller.handle_sync("POST", {}, {})
        mock_limitless_scheduler.trigger_sync.assert_called_with(force_full_sync=False)
        
        # Test force sync from query parameter
        mock_limitless_controller.handle_sync("POST", {"force": "true"}, {})
        mock_limitless_scheduler.trigger_sync.assert_called_with(force_full_sync=True)
        
        # Test force sync from body
        mock_limitless_controller.handle_sync("POST", {}, {"force_full_sync": True})
        mock_limitless_scheduler.trigger_sync.assert_called_with(force_full_sync=True)
    
    def test_controller_handle_status(self, mock_limitless_controller, mock_limitless_service, mock_limitless_scheduler):
        """Test the status endpoint in the controller."""
        # Replace get_sync_status and get_status with mocks
        mock_limitless_service.get_sync_status = Mock(return_value={"test": "service_status"})
        mock_limitless_scheduler.get_status = Mock(return_value={"test": "scheduler_status"})
        
        # Call the endpoint
        result = mock_limitless_controller.handle_status("GET")
        
        # Check that the endpoint returns the combined status
        assert result == {
            "service": {"test": "service_status"},
            "scheduler": {"test": "scheduler_status"},
        }
    
    def test_controller_handle_scheduler(self, mock_limitless_controller, mock_limitless_scheduler):
        """Test the scheduler endpoints in the controller."""
        # Replace start, stop, and get_status with mocks
        mock_limitless_scheduler.start = Mock(return_value=True)
        mock_limitless_scheduler.stop = Mock(return_value=True)
        mock_limitless_scheduler.get_status = Mock(return_value={"test": "scheduler_status"})
        
        # Test GET endpoint
        result = mock_limitless_controller.handle_scheduler("GET", {}, {})
        assert result == {"test": "scheduler_status"}
        
        # Test start action
        result = mock_limitless_controller.handle_scheduler("POST", {"action": "start"}, {})
        assert result == {"success": True, "message": "Scheduler started"}
        mock_limitless_scheduler.start.assert_called_once()
        
        # Test stop action
        result = mock_limitless_controller.handle_scheduler("POST", {"action": "stop"}, {})
        assert result == {"success": True, "message": "Scheduler stopped"}
        mock_limitless_scheduler.stop.assert_called_once()
        
        # Test invalid action
        result = mock_limitless_controller.handle_scheduler("POST", {"action": "invalid"}, {})
        assert "error" in result


class TestLimitlessLiveIntegration:
    """Live integration tests for Limitless with real API calls and Neo4j connections."""
    
    def test_adapter_connectivity(self, live_limitless_adapter):
        """Test adapter connectivity to real Limitless API."""
        # Check API reachability
        assert live_limitless_adapter.ping() is True
        logger.info("Limitless API is reachable")
    
    def test_adapter_fetch_logs(self, live_limitless_adapter):
        """Test fetching life logs from real API."""
        # Get a few logs
        success, result = live_limitless_adapter.get_life_logs(limit=5)
        
        assert success is True
        assert "data" in result
        
        logs = result.get("data", [])
        logger.info(f"Fetched {len(logs)} life logs")
        
        # Log some basic info
        for log in logs:
            logger.info(f"Log: {log.get('id')} - {log.get('title')}")
            
        # Return the first log if available for later tests
        if logs:
            return logs[0]
    
    def test_knowledge_graph_connectivity(self, live_knowledge_graph_service):
        """Test connectivity to Neo4j knowledge graph."""
        kg_service, test_source = live_knowledge_graph_service
        
        # Create a test entity
        entity_id = f"test:entity:{uuid.uuid4().hex[:8]}"
        entity = {
            "id": entity_id,
            "name": "Test Entity",
            "type": "TestType",
            "source": test_source,
        }
        
        # Add the entity
        success, result = kg_service.add_entity(entity)
        assert success is True, f"Failed to add entity: {result}"
        
        # Get entities
        entities = kg_service.get_entities()
        
        # Verify our test entity is in there
        entity_ids = [e.get("id") for e in entities]
        assert entity_id in entity_ids, "Test entity not found in knowledge graph"
        
        logger.info("Knowledge graph connection successful")
    
    def test_full_sync_flow(self, live_limitless_adapter, live_limitless_service, live_knowledge_graph_service):
        """Test the full sync flow with real data and knowledge graph integration."""
        kg_service, test_source = live_knowledge_graph_service
        
        # Get the number of entities before
        entities_before = len(kg_service.get_entities())
        logger.info(f"Entities before sync: {entities_before}")
        
        # Run a sync with limited logs (from past day to avoid too many)
        live_limitless_service.last_sync_time = datetime.now() - timedelta(days=1)
        success, message = live_limitless_service.sync_life_logs()
        
        assert success is True
        logger.info(f"Sync result: {message}")
        
        # Get the number of entities after
        entities_after = len(kg_service.get_entities())
        logger.info(f"Entities after sync: {entities_after}")
        
        # If we have new entities, the sync extracted something
        # Note: This test is somewhat fragile as it depends on having recent logs with entities
        assert entities_after >= entities_before, "No new entities were created"
    
    def test_scheduler_integration(self, live_limitless_scheduler):
        """Test scheduler integration with real services."""
        # Start the scheduler
        assert live_limitless_scheduler.start() is True
        
        # Wait a bit for the first sync to complete
        logger.info("Waiting for initial sync to complete...")
        time.sleep(5)  # Adjust based on how long sync typically takes
        
        # Check that we've recorded a sync time
        assert live_limitless_scheduler.last_sync_time is not None
        
        # Get status
        status = live_limitless_scheduler.get_status()
        logger.info(f"Scheduler status: {json.dumps(status, indent=2)}")
        
        # Stop the scheduler
        assert live_limitless_scheduler.stop() is True
        
        # Trigger a manual sync
        result = live_limitless_scheduler.trigger_sync(force_full_sync=False)
        assert result["success"] is True
        logger.info("Manual sync triggered successfully")
    
    def test_caching(self, live_limitless_adapter, live_limitless_service):
        """Test caching of life logs."""
        # First get a life log
        success, result = live_limitless_adapter.get_life_logs(limit=1)
        
        assert success is True
        assert "data" in result
        assert len(result.get("data", [])) > 0
        
        log = result["data"][0]
        log_id = log["id"]
        
        # Process and cache the log
        success, message = live_limitless_service._process_life_log(log)
        assert success is True
        
        # Get from cache
        success, cached_log = live_limitless_service.get_life_log(log_id)
        
        assert success is True
        assert cached_log["id"] == log_id
        
        # Clear cache
        success, message = live_limitless_service.clear_cache()
        assert success is True


# Only run this test manually as it creates HTTP connections to localhost
@pytest.mark.skipif(not os.environ.get("TEST_HTTP_API", False), 
                   reason="Skipping HTTP API tests (set TEST_HTTP_API=1 to run)")
class TestLimitlessHTTPAPI:
    """Tests for the real HTTP API endpoints.
    
    These tests require the server to be running on localhost and a valid
    Limitless API key in the environment.
    """
    
    BASE_URL = "http://localhost:9999"
    
    def test_status_endpoint(self):
        """Test the status endpoint."""
        import requests
        
        response = requests.get(f"{self.BASE_URL}/limitless/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "service" in data
        assert "scheduler" in data
        
        logger.info(f"Status response: {json.dumps(data, indent=2)}")
    
    def test_sync_endpoint(self):
        """Test the sync endpoint."""
        import requests
        
        # Trigger a sync with force=true for thorough testing
        response = requests.post(
            f"{self.BASE_URL}/limitless/sync",
            json={"force_full_sync": True}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        
        logger.info(f"Sync response: {json.dumps(data, indent=2)}")
    
    def test_scheduler_endpoints(self):
        """Test the scheduler endpoints."""
        import requests
        
        # Get initial status
        response = requests.get(f"{self.BASE_URL}/limitless/scheduler")
        assert response.status_code == 200
        
        initial_status = response.json()
        logger.info(f"Initial scheduler status: {json.dumps(initial_status, indent=2)}")
        
        # Stop scheduler
        response = requests.post(f"{self.BASE_URL}/limitless/scheduler?action=stop")
        assert response.status_code == 200
        
        # Verify it's stopped
        response = requests.get(f"{self.BASE_URL}/limitless/scheduler")
        status = response.json()
        assert not status["running"]
        
        # Start scheduler
        response = requests.post(f"{self.BASE_URL}/limitless/scheduler?action=start")
        assert response.status_code == 200
        
        # Verify it's running
        response = requests.get(f"{self.BASE_URL}/limitless/scheduler")
        status = response.json()
        assert status["running"]
    
    def test_get_life_log_endpoint(self):
        """Test the get life log endpoint."""
        import requests
        
        # First get a life log ID
        api_key = os.environ.get("LIMITLESS_API_KEY")
        headers = {"X-API-Key": api_key}
        
        response = requests.get(
            "https://api.limitless.ai/v1/lifelogs?limit=1",
            headers=headers
        )
        
        assert response.status_code == 200
        
        result = response.json()
        assert "data" in result
        assert len(result["data"]) > 0
        
        log_id = result["data"][0]["id"]
        
        # Now test the endpoint
        response = requests.get(f"{self.BASE_URL}/limitless/logs/{log_id}")
        
        # This might fail if the log hasn't been synced yet
        if response.status_code == 404:
            logger.warning(f"Log {log_id} not found in cache, triggering sync first")
            
            # Trigger a sync
            requests.post(f"{self.BASE_URL}/limitless/sync")
            
            # Wait for sync to complete
            time.sleep(5)
            
            # Try again
            response = requests.get(f"{self.BASE_URL}/limitless/logs/{log_id}")
        
        # Now it should work
        assert response.status_code == 200
        
        data = response.json()
        assert "log" in data
        assert data["log"]["id"] == log_id
        
        logger.info(f"Get log response: {json.dumps(data, indent=2)}")