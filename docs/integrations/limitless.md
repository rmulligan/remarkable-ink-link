# Limitless Life Log Integration

This document provides an overview of the Limitless Life Log integration with InkLink, explaining how it works, how to set it up, and how to test it.

## Overview

The Limitless Life Log integration allows InkLink to automatically retrieve life logs from the Limitless AI API and integrate them into the knowledge graph. This enables several key features:

1. Automatic syncing of life logs to the knowledge graph at regular intervals
2. Extraction of entities and relationships from life log content
3. Semantic connection between life logs and other knowledge entities
4. Scheduled syncing with configurable intervals

## Components

The integration consists of the following components:

1. **LimitlessAdapter**: Handles direct communication with the Limitless API, including authentication, pagination, and error handling.
2. **LimitlessLifeLogService**: Manages the processing of life logs, extraction of entities and relationships, and integration with the knowledge graph.
3. **LimitlessSchedulerService**: Provides scheduling functionality for automated syncing of life logs at regular intervals.

## Setup

### Environment Variables

The integration requires the following environment variables:

```
LIMITLESS_API_KEY=your_api_key_here
NEO4J_URI=bolt://localhost:7687 (optional, default value shown)
NEO4J_USER=neo4j (optional, default value shown)
NEO4J_PASS=password (optional, default value shown)
```

You can set these environment variables in several ways:

1. In a `.env` file in the project root directory (recommended for development)
2. In your shell environment (e.g., export in .bashrc or .zshrc)
3. Via direnv using the .envrc file
4. Directly when running commands: `LIMITLESS_API_KEY=xxx poetry run ...`

### Direnv Setup

For the best development experience, we recommend using direnv to automatically load environment variables:

1. Make sure direnv is installed on your system
2. Create a `.env` file with your environment variables
3. The project already has an `.envrc` file that loads variables from `.env`

## Testing

### Running Tests

To run the Limitless integration tests:

```bash
# Run all Limitless tests
./run_limitless_tests.sh

# Run a specific test
./run_limitless_tests.sh ::TestLimitlessLiveIntegration::test_end_to_end_flow
```

The test script automatically:
1. Loads environment variables from `.env`
2. Activates the Python virtual environment
3. Runs the specified tests with pytest

### Test Structure

The tests are organized into two main classes:

1. **TestLimitlessLiveIntegration**: Tests the core functionality with the real API
   - `test_limitless_adapter_ping`: Verifies API connectivity
   - `test_limitless_adapter_get_life_logs`: Tests fetching life logs
   - `test_limitless_adapter_get_all_life_logs`: Tests pagination functionality
   - `test_limitless_service_sync_logs`: Tests syncing logs to the knowledge graph
   - `test_limitless_scheduler`: Tests scheduler start/stop functionality
   - `test_limitless_manual_trigger`: Tests manual triggering of syncs
   - `test_end_to_end_flow`: Tests the complete flow from API to knowledge graph

2. **TestLimitlessHTTPAPI**: Tests the HTTP endpoints (requires server to be running)
   - These tests are skipped by default; enable with TEST_HTTP_API=1

## API Response Format

The Limitless API returns life logs in the following format:

```json
{
  "data": {
    "lifelogs": [
      {
        "id": "unique_id",
        "title": "Log title",
        "markdown": "Markdown content...",
        "contents": [
          {
            "content": "Content item text",
            "type": "heading1|heading2|heading3|blockquote|etc",
            "startTime": "ISO timestamp", 
            "endTime": "ISO timestamp",
            "speakerName": "Speaker name",
            "startOffsetMs": 1000,
            "endOffsetMs": 2000
          }
        ],
        "startTime": "ISO timestamp",
        "endTime": "ISO timestamp"
      }
    ]
  },
  "meta": {
    "lifelogs": {
      "count": 5,
      "nextCursor": "cursor_for_pagination"
    }
  }
}
```

## Known Issues

1. **Response Format Variability**: The API response format has multiple nesting patterns. The adapter handles different response structures, but if you encounter errors, check the exact structure returned by the API.

2. **Gateway Timeouts**: The Limitless API may experience gateway timeouts (HTTP 504) when:
   - Fetching specific logs by ID
   - Making too many requests in rapid succession
   - Paginating through many pages of results

   To mitigate these issues:
   - Add appropriate retry logic with exponential backoff
   - Implement caching for frequently accessed logs
   - Limit concurrent requests to the API

3. **Knowledge Graph Integration**: Knowledge graph integration requires a Neo4j database. For testing without Neo4j, a mock service is used in the test suite.

## Troubleshooting

1. **API Key Issues**: Ensure your API key is correctly set in the environment.
2. **Connection Issues**: Check that you can reach the Limitless API with a simple HTTP request.
3. **Neo4j Connection**: Verify Neo4j connection settings if you're using a real database.

Run the `check_api.py` or `test_new_key.py` scripts to verify direct API connectivity:

```bash
LIMITLESS_API_KEY=your_key python check_api.py
```