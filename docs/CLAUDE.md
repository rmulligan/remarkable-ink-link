# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

InkLink connects reMarkable tablets with AI tooling for handwritten workflows, research, transcription, and task management. The core functionality converts web content, PDFs, and AI responses to native reMarkable ink format (.rm files), enabling users to interact with them just like handwritten notes.

## Key Commands

### Installation and Setup

```bash
# Install dependencies (Python via Poetry and other dependencies)
yarn

# Install Python dependencies only
poetry install

# Start the server with Docker (recommended)
yarn install:docker

# Build Docker image only
yarn docker:build

# Start Docker containers
yarn docker:up

# Stop Docker containers
yarn docker:down
```

### Authentication

```bash
# Start the authentication UI (accessible at http://127.0.0.1:8000/auth)
yarn auth
```

### Development

```bash
# Start the InkLink server (on port 9999 by default)
yarn start

# Run tests
yarn test

# Run a specific test file
poetry run pytest tests/test_file.py

# Run a specific test function
poetry run pytest tests/test_file.py::test_function

# Lint code
yarn lint

# Format code
yarn format
```

### Integration Testing

```bash
# Test MyScript Web API integration
python test_myscript_web_api.py

# Test handwriting web adapter (skip file tests if rmscene not installed)
python test_handwriting_web_adapter.py --skip-file-test

# Test Limitless integration
python test_limitless_api.py

# Run Limitless demo script
./scripts/run_limitless_demo.sh
```

### Deployment

```bash
# Deploy to a Raspberry Pi
chmod +x scripts/deploy_to_pi.sh
scripts/deploy_to_pi.sh
```

## Architecture

InkLink follows a service-oriented architecture with clear separation of concerns:

1. **HTTP Server Layer** (`server.py`): Handles HTTP endpoints including `/share`, `/ingest`, and others.

2. **Service Layer**:
   - `remarkable_service.py`: Interacts with reMarkable Cloud API
   - `document_service.py`: Converts content to reMarkable format
   - `web_scraper_service.py`: Extracts content from web pages
   - `pdf_service.py`: Processes PDF documents
   - `qr_service.py`: Generates QR codes for source linking
   - `ai_service.py`: Performs AI processing of content
   - `round_trip_service.py`: Handles the complete handwriting recognition and response flow
   - `handwriting_recognition_service.py`: Processes handwriting using Claude Vision
   - `knowledge_graph_service.py`: Manages the knowledge graph for entity and relationship storage
   - `limitless_life_log_service.py`: Manages Limitless Life Log integration

3. **Adapter Layer**:
   - `adapters/remarkable_adapter.py`: Interface to reMarkable API
   - `adapters/rmapi_adapter.py`: Low-level interactions with rmapi CLI
   - `adapters/handwriting_adapter.py`: Interface for handwriting recognition
   - `adapters/claude_vision_adapter.py`: Integration with Claude's vision capabilities
   - `adapters/handwriting_web_adapter.py`: MyScript Web API integration
   - `adapters/limitless_adapter.py`: Interface to Limitless API

4. **Dependency Injection** (`di/container.py`): Centralized provider for service instantiation and dependency resolution.

5. **Pipeline System** (`pipeline/`): Modular processing pipeline for content transformations.

6. **MCP Integration** (`mcp/`): Model Context Protocol tools for AI agent communication.

7. **Controllers** (`controllers/`): Handle HTTP request routing and response formatting.

8. **CLI Interface** (`main.py`): Provides commands via Click for server, auth, and other functions.

## Key Integrations

### Claude Vision Integration

Claude Vision provides handwriting recognition for reMarkable notebooks:
- Converting handwritten notes to text
- Processing mathematical expressions
- Recognizing diagrams and drawings
- Multi-page document processing

Configuration requires Claude CLI to be installed and accessible:
```bash
# Add to .env file
CLAUDE_COMMAND=claude
CLAUDE_MODEL=claude-3-opus-20240229  # or your preferred Claude model with vision
```

### Limitless Integration

The Limitless Life Log integration connects InkLink with the Limitless API, providing:
- Life log syncing to local storage
- Knowledge graph integration
- Automatic scheduled syncing
- API endpoints for manual sync and management

### Knowledge Graph Integration

The knowledge graph integration stores entities and relationships from reMarkable notebooks:
- Entity extraction and classification
- Relationship mapping
- Semantic connections
- Cross-notebook references
- Index generation for entities, topics, and notebooks

## Development Tips

1. **Environment Configuration**: The system uses environment variables with fallbacks defined in `config.py`:
   - Server settings (HOST, PORT)
   - File paths (TEMP_DIR, OUTPUT_DIR)
   - Tool paths (RMAPI_PATH, DRAWJ2D_PATH)
   - reMarkable settings (RM_FOLDER, PAGE_WIDTH, etc.)
   - API credentials (CLAUDE_COMMAND, CLAUDE_MODEL)

2. **Service Testing**: Most services have mocks in the test suite to avoid real external dependencies.

3. **Docker Workflow**: The recommended development approach is using Docker which ensures all dependencies (rmapi, drawj2d) are properly installed.

4. **Data Flow**: The typical data flow for web content:
   1. Receive URL via HTTP endpoint
   2. Generate QR code linking back to source
   3. Scrape and process web content
   4. Convert to HCL template
   5. Render to reMarkable format using drawj2d
   6. Upload to reMarkable Cloud via rmapi

5. **Handwriting Recognition Flow**:
   1. Download notebook from reMarkable Cloud
   2. Extract and render strokes to images
   3. Send images to Claude Vision for recognition
   4. Process recognized text for entities and relationships
   5. Generate and upload response to reMarkable

## Custom CLI Commands

InkLink provides several custom CLI commands (via `python -m inklink.main`):

```bash
# Start the HTTP server
python -m inklink.main server

# Run the auth server
python -m inklink.main auth

# Ask a question to AI and upload response to reMarkable
python -m inklink.main ask --prompt "Your question here"

# Process handwritten query and generate response
python -m inklink.main roundtrip --input_file path/to/file.rm

# Knowledge graph index generation commands
python -m inklink.main create_entity_index
python -m inklink.main create_topic_index
python -m inklink.main create_notebook_index
python -m inklink.main create_master_index

# Monitor reMarkable Cloud for tagged notebooks
python -m inklink.main monitor --tag "Cass"

# Start Lilly assistant to process handwritten notes
python -m inklink.main lilly --tag "Lilly"
```

### GitHub Commands

- Use the `gh command` to work with github pull requests