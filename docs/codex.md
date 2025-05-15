# Codex Project Guide: InkLink

## Project Overview
InkLink is a toolkit enabling users to interact with AI directly from their reMarkable tablet, bridging handwritten notes with digital services.

## Implementation Status (May 2025)

### Completed Features
- **Web-to-Ink Sharing**: HTTP server endpoint for URLs → reMarkable content
- **PDF Processing**: Detection, conversion of PDFs to editable ink
- **QR Code Generation**: Auto-adding QR codes linking to source
- **Authentication UI**: Web UI for reMarkable Cloud auth
- **Document Conversion**: Structured pipeline for native .rm generation
- **Docker Environment**: Containerized setup with dependencies

### In Progress
- **AI Integration**: LLM connectivity and response formatting
- **Handwriting Recognition**: MyScript iink SDK integration
- **UI-based Tag Actions**: UI elements for content tagging
- **Knowledge Graph**: Entity extraction from notes
- **Two-way Sync**: Push/pull content to/from reMarkable

## Primary Goals
- Convert AI/web responses into editable ink (.rm files)
- Implement UI-based tagging system for workflows
- Enable automatic sync via `rmapi`
- Support modular AI tool interaction via MCP

## Project Structure
- `src/inklink/`: Core Python package
  - `main.py`: Entry point with CLI commands
  - `server.py`: HTTP server for URL sharing endpoint
  - `auth.py`: FastAPI app for reMarkable auth UI
  - `config.py`: Configuration management
  - `utils.py`: Shared utilities
  - `services/`: Core service implementations
    - `document_service.py`: Converts content to HCL and .rm files
    - `pdf_service.py`: PDF detection and processing
    - `qr_service.py`: QR code generation
    - `remarkable_service.py`: Cloud upload via rmapi
    - `web_scraper_service.py`: Content extraction from web
    - `google_docs_service.py`: Google Docs integration
    - `interfaces.py`: Abstract base classes for services
- `scripts/`: CLI tools for syncing, deployment, etc.
- `tests/`: Test suite organized by component
- `docs/`: Design docs and implementation plans
- `Dockerfile` & `docker-compose.yml`: Container configuration
- `.github/workflows/`: CI/CD pipelines

## Dev Environment
- Use Python 3.10 with Poetry for dependency management
- Optional Node.js/Yarn for frontend components
- Docker and docker-compose for containerized dev/deployment
- Pre-commit hooks for code quality enforcement
- Pytest for unit and integration testing

## Service Layer Design
The InkLink architecture follows a service-oriented pattern:
- Services implement interfaces defined in `interfaces.py`
- Configuration flows from central `CONFIG` dictionary
- HTTP server routes requests through service layer
- Retry and error handling utilities for robustness
- Temporary file management for multi-stage processing

## Technical Implementation Guide

### Web Content Pipeline
1. **Content Extraction**: Scrape URL via requests/BeautifulSoup, structured into schema
2. **Content Processing**: Convert to internal structured format
3. **Layout Generation**: Create HCL script for layout with proper formatting
4. **Conversion**: Use drawj2d to render HCL as .rm compatible strokes
5. **Upload**: Send to reMarkable cloud via rmapi

### Handwriting Recognition Pipeline
1. **Stroke Extraction**: Parse .rm files via rmscene
2. **Format Conversion**: Transform to MyScript compatible format
3. **Recognition API Call**: Submit to MyScript iink SDK with HMAC auth
4. **Result Processing**: Parse JSON response for text content
5. **Optional Vision Model Verification**: Cross-check with vision model

### Tag-Based Actions Implementation
- **CRITICAL**: Implement using UI-selected tags only, NOT via handwriting recognition
- **Approach**:
  1. Provide UI components for tag selection/creation
  2. Associate tags with content via iinkTS API identifiers
  3. Implement action triggers in UI
  4. Execute actions by retrieving tagged content

### Knowledge Graph Integration
- First phase: Simple entity extraction with local models
- Second phase: Neo4j integration for relationship tracking 
- Data model: Notes, Tasks, Concepts, References with appropriate relationships
- Entity detection should leverage NER techniques with local models

## Code Quality Guidelines
- Follow Black and flake8 rules defined in configs
- Use type hints consistently
- Document public methods with docstrings
- Favor composition over inheritance
- Follow interface segregation principle
- Implement retry patterns for network operations
- Use proper error handling with meaningful messages
- Validate input data early in processing pipeline

## Outstanding Issues
- **#21**: Test missing for plain text input with mixed valid/invalid content (priority: high)
- **#31, #27**: Code quality issues requiring attention (priority: medium)
- **#22**: Refactor `_upload_with_n_flag` method for maintainability (priority: medium)
- **#23**: Extract HTML parsing logic into shared helper (priority: medium)
- **#36, #38**: Break down long content loops in `create_hcl` (priority: medium)
- Multiple low-priority code quality improvements:
  - Extract duplicate code into functions
  - Avoid conditionals in tests
  - Use named expressions to simplify code

## Implementation Roadmap
1. **Phase 1** (Current): Complete web content pipeline 
2. **Phase 2**: Google Docs integration with structured export
3. **Phase 3**: Mixed content handling (tables, images)
4. **Phase 4**: Optimize conversion with direct .rm writer prototype
5. **Phase 5**: Robust cloud upload with retry/backoff
6. **Phase 6**: Browser extension for direct sharing
7. **Phase 7**: Testing, CI/CD, and documentation

## MyScript Integration
- **Requirements**:
  - MyScript Developer account
  - API keys (Application + HMAC)
  - Understanding of usage limits
- **Architecture**: Client-server model where:
  - Client (iinkTS) captures strokes and renders results
  - Server performs recognition and processing
  - Network connectivity required for core functions
- **Integration Pattern**:
  - Format stroke data to MyScript JSON format
  - Send authenticated requests to MyScript API
  - Process JSON response with recognition results

## AI Integration Strategy
- **Hybrid Processing**:
  - MyScript iink SDK for primary handwriting recognition
  - Local vision models (Ollama) for validation and context
  - Neo4j for knowledge graph storage
- **Tool Calling Implementation**:
  - Define JSON schema for tool interfaces
  - Implement specialized tools for symbol detection, task management
  - Create orchestration layer for different AI services
- **Models & Resources**:
  - LLama 3.1 (8B) via Ollama for core processing
  - LLaVA 1.5 for vision/symbol tasks
  - Phi-3-Vision for additional capabilities

## Known Challenges
- Authentication security with HMAC-SHA512
- Network reliability for server-dependent features
- Configuration complexity with extensive options
- Styling limitations (no standard CSS)
- Browser compatibility requirements
- Content-type specific features/limitations
- Debugging complexity in client-server model

## GitHub Wiki Structure
- **Home.md**: Project overview and navigation
- **MyScript-Integration-Guide.md**: SDK setup and configuration
- **Tag-Based-Actions-Implementation.md**: UI design and data model
- **Technical-Architecture.md**: Component diagrams and flows
- **Development-Guide.md**: Environment setup and testing
- **API-Reference.md**: Internal APIs and integration points

## Documentation Standards
- Include last updated date on pages
- Use code blocks with syntax highlighting
- Document API methods with signatures and types
- Use consistent notation for diagrams
- Link between related concepts and external docs

## Critical Implementation Details
1. MyScript's client-server architecture requires network connectivity
2. UI-based approach to tags (NOT handwritten recognition)
3. Data model must support tag-content associations
4. Network requirements and error handling are critical
5. Configuration should support multiple content types
6. Browser compatibility must be maintained for UI components
7. LLM integration should follow the MCP protocol
8. Knowledge graph should start simple and grow in complexity