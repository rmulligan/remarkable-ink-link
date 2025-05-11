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

3. **Utility Layer**:
   - `utils/hcl_render.py`: Renders HCL templates for reMarkable
   - `utils/rcu.py`: Integrates with RCU (reMarkable Content Utilities)
   - Various other utilities for common operations

4. **CLI Interface** (`main.py`): Provides commands via Click for server, auth, and other functions

## Development Tips

1. **Environment Configuration**: The system uses environment variables with fallbacks defined in `config.py`:
   - Server settings (HOST, PORT)
   - File paths (TEMP_DIR, OUTPUT_DIR)
   - Tool paths (RMAPI_PATH, DRAWJ2D_PATH)
   - reMarkable settings (RM_FOLDER, PAGE_WIDTH, etc.)

2. **Service Testing**: Most services have mocks in the test suite to avoid real external dependencies.

3. **Docker Workflow**: The recommended development approach is using Docker which ensures all dependencies (rmapi, drawj2d) are properly installed.

4. **Data Flow**: The typical data flow for web content:
   1. Receive URL via HTTP endpoint
   2. Generate QR code linking back to source
   3. Scrape and process web content
   4. Convert to HCL template
   5. Render to reMarkable format using drawj2d
   6. Upload to reMarkable Cloud via rmapi

5. **Testing Strategy**:
   - Mock external dependencies
   - Test each service in isolation
   - End-to-end tests in `test_full_roundtrip.py`

## Code Quality

- Use black to format python and flake8 to check for project issues

## Memories

- Keep the documentation updated at README.md, the docs directory, and your own notes
- This project uses a virtual environment in .venv
- Run black formatter and flake8 before pushing
- GitHub MCP server is integrated for repository management, see docs/github_integration.md