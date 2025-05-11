"""Live integration test for Limitless Life Log.

This test script performs a complete live test of the Limitless integration
with real credentials. This requires the following environment variables:

- LIMITLESS_API_KEY: Your Limitless API key
- NEO4J_URI: URI for the Neo4j database (default: bolt://localhost:7687)
- NEO4J_USER: Neo4j username (default: neo4j)
- NEO4J_PASS: Neo4j password (default: password)

This test is skipped by default unless the LIMITLESS_API_KEY environment
variable is set.

Usage:
    To run with real credentials:
    LIMITLESS_API_KEY=your_api_key NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASS=password pytest -xvs tests/test_limitless_live.py
"""

import os
import time
import json
import logging
import pytest
from datetime import datetime, timedelta
import requests
import tempfile

from inklink.adapters.limitless_adapter import LimitlessAdapter
from inklink.services.limitless_life_log_service import LimitlessLifeLogService
from inklink.services.limitless_scheduler_service import LimitlessSchedulerService
from inklink.services.knowledge_graph_service import KnowledgeGraphService

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Check if we have credentials for live testing
has_limitless_key = bool(os.environ.get("LIMITLESS_API_KEY"))

# Skip tests if no credentials
if not has_limitless_key:
    pytestmark = pytest.mark.skip(reason="LIMITLESS_API_KEY not set")


@pytest.fixture
def limitless_adapter():
    """Create a real Limitless adapter with API key from environment."""
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
def knowledge_graph_service():
    """Create a real Knowledge Graph service with credentials from environment."""
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    username = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASS", "password")
    
    service = KnowledgeGraphService(
        uri=uri,
        username=username,
        password=password,
    )
    
    # Clean up test entities before and after test
    try:
        service.delete_entities_by_source("limitless_live_test")
    except Exception as e:
        logger.warning(f"Error during pre-test cleanup: {e}")
    
    yield service
    
    # Clean up after test
    try:
        service.delete_entities_by_source("limitless_live_test")
    except Exception as e:
        logger.warning(f"Error during post-test cleanup: {e}")


@pytest.fixture
def limitless_service(limitless_adapter, knowledge_graph_service):
    """Create a real Limitless Life Log service."""
    # Create temporary directory for storage
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = os.path.join(temp_dir, "limitless")
        os.makedirs(storage_path, exist_ok=True)
        
        service = LimitlessLifeLogService(
            limitless_adapter=limitless_adapter,
            knowledge_graph_service=knowledge_graph_service,
            sync_interval=3600,
            storage_path=storage_path,
        )
        
        yield service


@pytest.fixture
def limitless_scheduler(limitless_service):
    """Create a real Limitless scheduler."""
    scheduler = LimitlessSchedulerService(
        limitless_service=limitless_service,
        sync_interval=60,  # Short interval for testing
        initial_delay=1,   # Short delay for testing
    )
    
    yield scheduler
    
    # Ensure scheduler is stopped after test
    if scheduler.running:
        scheduler.stop()


class TestLimitlessLiveIntegration:
    """Live integration tests for Limitless."""
    
    def test_limitless_adapter_ping(self, limitless_adapter):
        """Test that the adapter can connect to the real Limitless API."""
        logger.info("Testing API connectivity...")
        assert limitless_adapter.ping() is True
        logger.info("API connectivity successful")
    
    def test_limitless_adapter_get_life_logs(self, limitless_adapter):
        """Test fetching life logs from the real API."""
        logger.info("Fetching life logs from API...")
        success, result = limitless_adapter.get_life_logs(limit=5)
        
        assert success is True
        assert "data" in result
        
        logs = result.get("data", [])
        logger.info(f"Successfully fetched {len(logs)} life logs")
        
        # Print out some basic info about the logs
        for log in logs:
            logger.info(f"Log ID: {log.get('id')}, Title: {log.get('title')}")
            
        return logs
    
    def test_limitless_adapter_get_all_life_logs(self, limitless_adapter):
        """Test fetching all life logs with pagination."""
        logger.info("Fetching all life logs from API (with pagination)...")
        # Get logs from the last 30 days to limit the result set
        from_date = datetime.now() - timedelta(days=30)
        
        start_time = time.time()
        success, logs = limitless_adapter.get_all_life_logs(from_date=from_date)
        end_time = time.time()
        
        assert success is True
        logger.info(f"Successfully fetched {len(logs)} life logs in {end_time - start_time:.2f} seconds")
    
    def test_limitless_service_sync_logs(self, limitless_service):
        """Test syncing life logs to the knowledge graph."""
        logger.info("Syncing life logs to knowledge graph...")
        
        # Sync logs from the last 7 days
        limitless_service.last_sync_time = datetime.now() - timedelta(days=7)
        
        start_time = time.time()
        success, message = limitless_service.sync_life_logs()
        end_time = time.time()
        
        assert success is True
        logger.info(f"Sync result: {message} in {end_time - start_time:.2f} seconds")
        
        # Check service status
        status = limitless_service.get_sync_status()
        logger.info(f"Service status: {json.dumps(status, indent=2)}")
    
    def test_limitless_scheduler(self, limitless_scheduler):
        """Test starting and stopping the scheduler."""
        logger.info("Testing scheduler start/stop...")
        
        # Start the scheduler
        assert limitless_scheduler.start() is True
        assert limitless_scheduler.running is True
        
        # Get status
        status = limitless_scheduler.get_status()
        logger.info(f"Scheduler status after start: {json.dumps(status, indent=2)}")
        
        # Wait a bit for the first sync to complete
        logger.info("Waiting for initial sync...")
        time.sleep(5)
        
        # Get updated status
        status = limitless_scheduler.get_status()
        logger.info(f"Scheduler status after initial sync: {json.dumps(status, indent=2)}")
        
        # Stop the scheduler
        assert limitless_scheduler.stop() is True
        assert limitless_scheduler.running is False
    
    def test_limitless_manual_trigger(self, limitless_scheduler):
        """Test manually triggering a sync."""
        logger.info("Testing manual sync trigger...")
        
        # Trigger sync with force=True to sync all logs
        result = limitless_scheduler.trigger_sync(force_full_sync=True)
        
        assert result["success"] is True
        logger.info(f"Manual sync result: {json.dumps(result, indent=2)}")
    
    def test_end_to_end_flow(self, limitless_adapter, limitless_service, limitless_scheduler):
        """Test the complete end-to-end flow of the Limitless integration."""
        logger.info("Running end-to-end flow test...")
        
        # 1. Fetch a specific life log
        logger.info("Step 1: Fetching a specific life log...")
        success, logs = limitless_adapter.get_life_logs(limit=1)
        assert success and logs.get("data"), "Failed to fetch life logs"
        
        sample_log = logs["data"][0]
        log_id = sample_log["id"]
        logger.info(f"Using log ID: {log_id}")
        
        # 2. Get specific life log
        logger.info("Step 2: Getting specific life log...")
        success, log = limitless_adapter.get_life_log_by_id(log_id)
        assert success, f"Failed to get life log with ID {log_id}"
        logger.info(f"Successfully retrieved log: {log.get('title')}")
        
        # 3. Process the life log
        logger.info("Step 3: Processing life log...")
        success, message = limitless_service._process_life_log(log)
        assert success, f"Failed to process life log: {message}"
        logger.info(f"Processing result: {message}")
        
        # 4. Save to cache
        logger.info("Step 4: Saving life log to cache...")
        limitless_service._save_life_log(log_id, log)
        
        # 5. Retrieve from cache
        logger.info("Step 5: Retrieving life log from cache...")
        success, cached_log = limitless_service.get_life_log(log_id)
        assert success, "Failed to retrieve log from cache"
        assert cached_log["id"] == log_id, "Cache returned wrong log"
        logger.info("Successfully retrieved log from cache")
        
        # 6. Start scheduler
        logger.info("Step 6: Starting scheduler...")
        limitless_scheduler.start()
        time.sleep(2)  # Wait for scheduler to initialize
        
        # 7. Get scheduler status
        logger.info("Step 7: Getting scheduler status...")
        status = limitless_scheduler.get_status()
        logger.info(f"Scheduler status: {json.dumps(status, indent=2)}")
        
        # 8. Stop scheduler
        logger.info("Step 8: Stopping scheduler...")
        limitless_scheduler.stop()
        
        # 9. Clear cache
        logger.info("Step 9: Clearing cache...")
        success, message = limitless_service.clear_cache()
        assert success, f"Failed to clear cache: {message}"
        logger.info(f"Cache clearing result: {message}")
        
        logger.info("End-to-end flow test completed successfully!")


@pytest.mark.skipif(not os.environ.get("TEST_HTTP_API", False), 
                   reason="Skipping HTTP API tests (set TEST_HTTP_API=1 to run)")
class TestLimitlessHTTPAPI:
    """Tests for the Limitless HTTP API endpoints.
    
    These tests require the server to be running locally on port 9999.
    """
    
    BASE_URL = "http://localhost:9999"
    
    def test_api_status_endpoint(self):
        """Test the /limitless/status endpoint."""
        response = requests.get(f"{self.BASE_URL}/limitless/status")
        assert response.status_code == 200
        
        data = response.json()
        logger.info(f"Status endpoint response: {json.dumps(data, indent=2)}")
        
        assert "service" in data
        assert "scheduler" in data
    
    def test_api_sync_endpoint(self):
        """Test the /limitless/sync endpoint."""
        response = requests.post(f"{self.BASE_URL}/limitless/sync", 
                                json={"force_full_sync": False})
        
        assert response.status_code == 200
        
        data = response.json()
        logger.info(f"Sync endpoint response: {json.dumps(data, indent=2)}")
        
        assert "success" in data
        assert "message" in data
    
    def test_api_scheduler_endpoints(self):
        """Test the /limitless/scheduler endpoints."""
        # Get scheduler status
        response = requests.get(f"{self.BASE_URL}/limitless/scheduler")
        assert response.status_code == 200
        
        status = response.json()
        logger.info(f"Scheduler status: {json.dumps(status, indent=2)}")
        
        # Start scheduler
        response = requests.post(f"{self.BASE_URL}/limitless/scheduler?action=start")
        assert response.status_code == 200
        
        result = response.json()
        logger.info(f"Start scheduler response: {json.dumps(result, indent=2)}")
        
        # Wait a bit
        time.sleep(2)
        
        # Stop scheduler
        response = requests.post(f"{self.BASE_URL}/limitless/scheduler?action=stop")
        assert response.status_code == 200
        
        result = response.json()
        logger.info(f"Stop scheduler response: {json.dumps(result, indent=2)}")
    
    def test_api_get_log_endpoint(self):
        """Test the /limitless/logs/{log_id} endpoint."""
        # First get logs from the adapter to get a valid ID
        api_key = os.environ.get("LIMITLESS_API_KEY")
        adapter = LimitlessAdapter(api_key=api_key)
        
        success, result = adapter.get_life_logs(limit=1)
        assert success and result.get("data"), "Failed to fetch life logs"
        
        log_id = result["data"][0]["id"]
        
        # Now test the API endpoint
        response = requests.get(f"{self.BASE_URL}/limitless/logs/{log_id}")
        assert response.status_code == 200
        
        data = response.json()
        logger.info(f"Get log endpoint response: {json.dumps(data, indent=2)}")
        
        assert "log" in data
        assert data["log"]["id"] == log_id