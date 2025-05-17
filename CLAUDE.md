# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

InkLink is an open-source toolkit that transforms your reMarkable tablet into an AI-augmented thought partner. It bridges paper-like thinking with intelligent workflows, allowing users to interact with AI-generated content in native reMarkable ink format (.rm files).

Key capabilities:
- Web-to-ink conversion (native, editable ink format)
- AI-augmented handwritten notes with Claude Vision recognition
- Tag-driven workflows (#summarize, #task, #calendar, #entity, #code)
- Knowledge graph generation from handwritten content
- MCP (Multi-Connection Protocol) agent framework
- Automatic sync with reMarkable Cloud

## Key Commands

### Installation and Setup
```bash
# Install all dependencies (Node.js + Python via Poetry)
yarn

# Install Python dependencies only
poetry install

# Start with Docker (recommended)
yarn install:docker

# Basic local installation
yarn install:bare
```

### Development Commands
```bash
# Start the InkLink server (port 9999)
yarn start
# or
poetry run inklink server

# Start authentication UI (http://127.0.0.1:8000/auth)
yarn auth
# or
poetry run inklink auth

# Run tests
yarn test
# or
poetry run pytest

# Run specific test
poetry run pytest tests/test_file.py::test_function

# Format code
yarn format
# or
poetry run black src tests

# Lint code  
yarn lint
# or
poetry run flake8 src tests
```

### Docker Commands
```bash
# Build Docker image
yarn docker:build

# Start containers
yarn docker:up

# Stop containers
yarn docker:down
```

### CLI Commands
```bash
# Ask AI question and upload response to reMarkable
python -m inklink.main ask --prompt "Your question here"

# Process handwritten query
python -m inklink.main roundtrip --input_file path/to/file.rm

# Monitor for tagged notebooks
python -m inklink.main monitor --tag "Cass"

# Start Lilly assistant
python -m inklink.main lilly --tag "Lilly"

# Knowledge graph management
python -m inklink.main create_entity_index
python -m inklink.main create_topic_index
python -m inklink.main create_notebook_index
python -m inklink.main create_master_index

# Ink-to-Code workflow
python -m inklink.main process_code --input_file path/to/file.rm
python -m inklink.main ink_to_code --notebook_id notebook-uuid
```

### Integration Testing
```bash
# Test MyScript Web API
python test_myscript_web_api.py

# Test handwriting adapter
python test_handwriting_web_adapter.py --skip-file-test

# Test Limitless integration
python test_limitless_api.py
./scripts/run_limitless_demo.sh

# Live testing scripts
./scripts/run_live_test.sh
./scripts/run_live_penpal_test.py
```

### Deployment
```bash
# Deploy to Raspberry Pi
chmod +x scripts/deploy_to_pi.sh
scripts/deploy_to_pi.sh
```

## Architecture

InkLink follows a modular, service-oriented architecture:

### Core Layers
1. **HTTP Server** (`server.py`): Handles API endpoints (/share, /ingest, /roundtrip)
2. **Controllers** (`controllers/`): Route requests and format responses  
3. **Services** (`services/`): Business logic and external integrations
4. **Adapters** (`adapters/`): Interface with external APIs and tools
5. **Pipeline** (`pipeline/`): Modular content processing pipeline
6. **MCP** (`mcp/`): Model Context Protocol for agent communication
7. **Dependency Injection** (`di/container.py`): Service instantiation and dependency resolution

### Core Services
- `remarkable_service.py`: reMarkable Cloud API interaction
- `document_service.py`: Content to .rm format conversion
- `ai_service.py`: AI model orchestration
- `round_trip_service.py`: Handwriting recognition and response flow
- `handwriting_recognition_service.py`: Claude Vision processing
- `knowledge_graph_service.py`: Entity and relationship management
- `limitless_life_log_service.py`: Limitless pendant integration

### Key Adapters
- `remarkable_adapter.py`: reMarkable API interface
- `rmapi_adapter.py`: Low-level rmapi CLI wrapper
- `claude_vision_adapter.py`: Claude Vision for handwriting recognition
- `handwriting_web_adapter.py`: MyScript Web API integration
- `limitless_adapter.py`: Limitless API interface

### Integration Points
- **Claude Vision**: Handwriting recognition (requires Claude CLI)
- **Limitless**: Audio capture and life logging
- **MyScript**: Alternative handwriting recognition
- **Knowledge Graph**: Entity extraction and semantic connections
- **MCP Tools**: Inter-agent communication protocol

## Configuration

Environment variables (defined in `config.py`):
- Server: `HOST`, `PORT`
- Paths: `TEMP_DIR`, `OUTPUT_DIR`
- reMarkable: `RM_FOLDER`, `PAGE_WIDTH`, `PAGE_HEIGHT`
- Tools: `RMAPI_PATH`, `DRAWJ2D_PATH`
- AI: `CLAUDE_COMMAND`, `CLAUDE_MODEL`
- Auth: Stored in `auth_controller.py`

## Development Workflow

1. Docker is recommended for consistent dependency management
2. Services have mock implementations for testing
3. Data flow for web content:
   - URL → QR code generation → Web scraping
   - Content → HCL template → drawj2d rendering  
   - Final .rm file → reMarkable upload via rmapi
4. Handwriting recognition flow:
   - Download notebook → Extract strokes → Claude Vision
   - Text recognition → Entity extraction → Knowledge graph
   - AI response → .rm format → Upload to reMarkable

## Testing

- Unit tests cover core services and adapters
- Integration tests verify external API connections
- Mock services available for isolated testing
- Use `pytest` with specific test markers for different scopes

## MCP Tools

InkLink provides several MCP tools for agent communication:
- `knowledge_graph_tools.py`: Graph manipulation
- `augmented_notebook_tools.py`: Notebook processing
- `knowledge_index_tools.py`: Index generation
- `registry.py`: Tool registration and discovery

## GitHub Integration

Use the `gh` command for pull request operations.

## Dependencies

Core dependencies managed by Poetry:
- Python 3.10+
- Node.js and Yarn  
- Docker (optional but recommended)
- Claude CLI (for vision-based handwriting recognition)
- rmapi (for reMarkable Cloud interaction)
- drawj2d (for ink rendering)