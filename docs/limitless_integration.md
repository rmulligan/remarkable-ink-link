# Limitless Life Log Integration

This document describes the integration between InkLink and Limitless Life Log, allowing users to synchronize their life logs into the knowledge graph for enhanced note-taking and knowledge management workflows.

## Overview

The Limitless Life Log integration allows InkLink to:

1. Automatically sync life logs from the Limitless API
2. Extract entities and relationships from life log content
3. Add the extracted knowledge to the knowledge graph
4. Link between reMarkable notebooks and Limitless life logs
5. Provide API endpoints for manual syncing and management

## Configuration

To enable the Limitless integration, you need to configure the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LIMITLESS_API_KEY` | API key for Limitless (required) | None |
| `LIMITLESS_API_URL` | Base URL for Limitless API | https://api.limitless.ai |
| `LIMITLESS_SYNC_INTERVAL` | Interval in seconds between syncs | 3600 (1 hour) |
| `LIMITLESS_STORAGE_PATH` | Path to store sync state and cached logs | {TEMP_DIR}/limitless |
| `LIMITLESS_AUTOSTART` | Whether to automatically start the scheduler | true |

## API Endpoints

The following API endpoints are available for interacting with the Limitless integration:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/limitless/sync` | POST | Trigger a manual sync |
| `/limitless/status` | GET | Get sync status information |
| `/limitless/logs/{log_id}` | GET | Get a specific life log by ID |
| `/limitless/scheduler` | GET | Get scheduler status |
| `/limitless/scheduler?action=start` | POST | Start the scheduler |
| `/limitless/scheduler?action=stop` | POST | Stop the scheduler |
| `/limitless/cache` | DELETE | Clear the life log cache |

### Examples

#### Trigger a manual sync

```bash
curl -X POST http://localhost:9999/limitless/sync
```

To force a full sync of all life logs (ignoring the last sync time):

```bash
curl -X POST http://localhost:9999/limitless/sync?force=true
```

#### Get sync status

```bash
curl http://localhost:9999/limitless/status
```

#### Start/stop the scheduler

```bash
curl -X POST http://localhost:9999/limitless/scheduler?action=start
curl -X POST http://localhost:9999/limitless/scheduler?action=stop
```

## Knowledge Graph Integration

Life logs are integrated into the knowledge graph as follows:

1. Each life log becomes a `LifeLog` entity in the graph
2. Entities (people, places, topics, etc.) are extracted from the log content
3. Relationships between entities are extracted
4. Life logs are linked to entities via `MENTIONS` relationships
5. Life logs can be linked to reMarkable notebooks via manual annotations

## Troubleshooting

Common issues and their solutions:

1. **Life logs not syncing**: Ensure the API key is correctly configured and the Limitless API is reachable. Check the logs for error messages.

2. **Scheduler not running**: Use the `/limitless/scheduler` endpoint to check the status and start the scheduler if needed.

3. **Entities not extracted**: The entity extraction is based on the knowledge graph service's capabilities. Ensure it is correctly configured and working.

## Implementation Details

The Limitless integration consists of the following components:

1. **LimitlessAdapter**: Handles communication with the Limitless API
2. **LimitlessLifeLogService**: Manages syncing and processing of life logs
3. **LimitlessSchedulerService**: Provides automatic syncing at regular intervals
4. **LimitlessController**: Handles HTTP endpoints for the Limitless integration

For more details, refer to the source code and unit tests.

## Future Improvements

Potential future improvements to the Limitless integration:

1. Add support for websocket notifications when new life logs are available
2. Enhance entity extraction with Limitless-specific topic modeling
3. Add two-way integration with ability to create life logs from reMarkable notes
4. Implement visualization of life log entities and relationships
5. Add support for custom life log templates and formats