# Limitless Life Log Integration Guide

This guide provides detailed information on setting up, configuring, and testing the Limitless Life Log integration with InkLink.

## Table of Contents

1. [Overview](#overview)
2. [Configuration](#configuration)
3. [API Endpoints](#api-endpoints)
4. [Testing](#testing)
5. [Development Guide](#development-guide)
6. [Troubleshooting](#troubleshooting)

## Overview

The Limitless Life Log integration connects InkLink with the Limitless API to synchronize life logs into the knowledge graph. This integration enables:

- **Automatic synchronization** of Limitless Life Logs
- **Entity and relationship extraction** from life log content
- **Knowledge graph integration** for semantic search and exploration
- **Scheduled syncing** to keep data up-to-date
- **Cached access** to life logs for improved performance

The integration consists of the following components:

1. **`LimitlessAdapter`**: Handles communication with the Limitless API
2. **`LimitlessLifeLogService`**: Manages syncing and processing of life logs
3. **`LimitlessSchedulerService`**: Provides automatic syncing at regular intervals
4. **`LimitlessController`**: Handles HTTP endpoints for the integration

## Configuration

### Environment Variables

The integration is configured using the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LIMITLESS_API_KEY` | API key for Limitless authentication (required) | None |
| `LIMITLESS_API_URL` | Base URL for the Limitless API | https://api.limitless.ai |
| `LIMITLESS_SYNC_INTERVAL` | Interval between syncs in seconds | 3600 (1 hour) |
| `LIMITLESS_STORAGE_PATH` | Path to store sync state and cached logs | {TEMP_DIR}/limitless |
| `LIMITLESS_AUTOSTART` | Whether to automatically start the scheduler | true |

### Configuration Methods

You can configure the integration in several ways:

#### 1. Environment Variables

```bash
export LIMITLESS_API_KEY=your_api_key
export LIMITLESS_SYNC_INTERVAL=1800  # 30 minutes
export LIMITLESS_AUTOSTART=true
```

#### 2. Docker Compose

```yaml
services:
  inklink:
    image: inklink
    environment:
      - LIMITLESS_API_KEY=your_api_key
      - LIMITLESS_SYNC_INTERVAL=1800
      - LIMITLESS_AUTOSTART=true
```

#### 3. Command Line

```bash
LIMITLESS_API_KEY=your_api_key LIMITLESS_SYNC_INTERVAL=1800 yarn start
```

## API Endpoints

The Limitless integration provides the following HTTP endpoints:

### Sync Endpoints

#### GET /limitless/status

Get current sync status, including cached log count, last sync time, and next scheduled sync.

**Example Response:**
```json
{
  "service": {
    "last_sync_time": "2023-07-15T12:34:56.789012",
    "cached_log_count": 42,
    "sync_interval": 3600,
    "next_sync_time": "2023-07-15T13:34:56.789012"
  },
  "scheduler": {
    "running": true,
    "sync_status": "idle",
    "last_sync_time": "2023-07-15T12:34:56.789012",
    "next_sync_time": "2023-07-15T13:34:56.789012",
    "sync_interval": 3600
  }
}
```

#### POST /limitless/sync

Trigger a manual sync of life logs.

**Query Parameters:**
- `force` (boolean, optional): If `true`, sync all life logs regardless of last sync time

**Request Body:**
```json
{
  "force_full_sync": true
}
```

**Example Response:**
```json
{
  "success": true,
  "message": "Successfully synced 42 life logs",
  "timestamp": "2023-07-15T12:34:56.789012",
  "next_sync": "2023-07-15T13:34:56.789012"
}
```

### Scheduler Endpoints

#### GET /limitless/scheduler

Get current scheduler status.

**Example Response:**
```json
{
  "running": true,
  "sync_status": "idle",
  "last_sync_time": "2023-07-15T12:34:56.789012",
  "next_sync_time": "2023-07-15T13:34:56.789012",
  "sync_interval": 3600,
  "service_status": {
    "last_sync_time": "2023-07-15T12:34:56.789012",
    "cached_log_count": 42,
    "sync_interval": 3600,
    "next_sync_time": "2023-07-15T13:34:56.789012"
  }
}
```

#### POST /limitless/scheduler?action=start

Start the scheduler.

**Example Response:**
```json
{
  "success": true,
  "message": "Scheduler started"
}
```

#### POST /limitless/scheduler?action=stop

Stop the scheduler.

**Example Response:**
```json
{
  "success": true,
  "message": "Scheduler stopped"
}
```

### Life Log Endpoints

#### GET /limitless/logs/{log_id}

Get a specific life log by ID.

**Example Response:**
```json
{
  "log": {
    "id": "log123",
    "title": "Meeting Notes",
    "content": "Had a productive meeting with the team...",
    "created_at": "2023-07-15T10:00:00Z",
    "metadata": {
      "tags": ["meeting", "notes"],
      "location": "Conference Room A"
    }
  }
}
```

### Cache Management

#### DELETE /limitless/cache

Clear the local cache of life logs.

**Example Response:**
```json
{
  "success": true,
  "message": "Successfully cleared life log cache"
}
```

## Testing

### Running Unit Tests

The integration includes comprehensive unit tests that can be run with or without real credentials:

```bash
# Run mock tests (no real API calls)
poetry run pytest tests/test_limitless_integration.py

# Run live tests with real credentials
LIMITLESS_API_KEY=your_api_key poetry run pytest tests/test_limitless_live.py
```

### Demo Script

A demo script is provided to test the integration with real credentials:

```bash
# Run the demo
./scripts/run_limitless_demo.sh your_api_key
```

The script will:
1. Set up necessary environment variables
2. Start the server if not already running
3. Test various API endpoints
4. Show the status and results

### End-to-End Testing

For comprehensive end-to-end testing of the integration, use the full integration test suite:

```bash
# Run mock tests
poetry run pytest tests/test_limitless_integration_full.py::TestLimitlessMockIntegration

# Run live tests
LIMITLESS_API_KEY=your_api_key poetry run pytest tests/test_limitless_integration_full.py::TestLimitlessLiveIntegration

# Run HTTP API tests (requires server running)
LIMITLESS_API_KEY=your_api_key TEST_HTTP_API=1 poetry run pytest tests/test_limitless_integration_full.py::TestLimitlessHTTPAPI
```

## Development Guide

### Architecture

The Limitless integration follows a layered architecture:

1. **Adapter Layer**: Handles communication with the Limitless API
2. **Service Layer**: Processes life logs and integrates with the knowledge graph
3. **Scheduler Layer**: Manages automatic syncing
4. **Controller Layer**: Exposes HTTP endpoints

### Adding Features

To add new features to the Limitless integration:

1. **Extend the adapter** for new API functionalities
2. **Update the service** to process and handle new data
3. **Modify the controller** to expose new endpoints
4. **Add tests** for the new features

### Knowledge Graph Integration

Life logs are integrated into the knowledge graph as follows:

1. Each life log becomes a `LifeLog` entity in the graph
2. Entities (people, places, topics, etc.) are extracted from the content
3. Relationships between entities are extracted
4. Life logs are linked to entities via `MENTIONS` relationships

This structure enables:
- Semantic search across life logs
- Exploration of connections between entities
- Tracking of topics and themes over time

## Troubleshooting

### Common Issues

#### "API key not found" or "API authentication failed"

- Ensure `LIMITLESS_API_KEY` is set correctly
- Check that the API key is valid and has the necessary permissions
- Verify that the API key is being properly passed in the `X-API-Key` header

#### "Scheduler not running" or "Sync not completing"

- Check if `LIMITLESS_AUTOSTART` is set to `true`
- Manually start the scheduler with `POST /limitless/scheduler?action=start`
- Verify that the Limitless API is reachable with `GET /limitless/status`

#### "No entities extracted from life logs"

- Ensure the Neo4j database is properly configured and reachable
- Check that the knowledge graph service is correctly extracting entities
- Verify that the life logs contain meaningful content for entity extraction

#### "Cache errors" or "Storage issues"

- Verify that the storage path (`LIMITLESS_STORAGE_PATH`) is writable
- Check disk space and permissions
- Try clearing the cache with `DELETE /limitless/cache`

### Logs and Diagnostics

When troubleshooting, check the following logs:

- Server logs for API endpoint errors
- Knowledge graph logs for extraction and database issues
- Limitless adapter logs for API communication problems

Increase log verbosity by setting:

```bash
export LOG_LEVEL=DEBUG
```

### Getting Help

If you need further assistance:

1. Check the [Limitless API documentation](https://www.limitless.ai/developers)
2. Review the source code and inline documentation
3. Run the tests with increased verbosity: `pytest -xvs tests/test_limitless_*`
4. Contact the development team with detailed error information