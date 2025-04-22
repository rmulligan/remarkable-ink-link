# Codex Project Guide: InkLink

## Project Overview
InkLink is a toolkit enabling users to interact with AI directly from their reMarkable tablet, bridging handwritten notes with digital services.

## Implementation Status (April 2025)

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

## Structure
- `scripts/`: CLI tools for syncing, formatting, etc.
- `formatters/`: drawj2d-compatible layout generators
- `handlers/`: AI-triggered tools (summarizers, extractors)
- `config/`: MCP tool definitions and user preferences

## Dev Notes
- Use ddvk fork of `rmapi` at `~/Projects/rmapi`
- Target `.rm` file generation from markdown/text
- Use prompt-based generation of HCL layout
- Make CLI scaffolding cross-platform where possible

## Style Guidelines
- Be modular and testable
- Favor `stdin`/`stdout` communication (MCP-friendly)
- Format AI responses for reMarkable-appropriate layout

---

## Technical Implementation Guide

### reMarkable Stroke Data Extraction
- **ricklupton/rmscene**: Key Python library for parsing .rm files
  - Install: `pip install rmscene`
  - Access: `notebook = rmscene.read_rm_file(path)`
  - Structure: RMNotebook → Scene → Layer → Stroke → Point
  - Point data: x, y, speed, direction, width, pressure

### MyScript Integration
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

### Tag-Based Actions Implementation
- **CRITICAL**: Implement using UI-selected tags only, NOT via handwriting recognition
- **Approach**:
  1. Provide UI components for tag selection/creation
  2. Associate tags with content via iinkTS API identifiers
  3. Implement action triggers in UI
  4. Execute actions by retrieving tagged content

### reMarkable App Persistence
- **Challenge**: Updates overwrite system partitions
- **Strategies**:
  - Store in `/home/root` or `/opt` (via Toltec/Entware)
  - Package using Toltec format
  - Use systemd user services in `/home/root/.config/systemd/user/`
  - Implement update recovery scripts

### Knowledge Graph Integration
- Consider on-device (resource-constrained) vs. off-device processing
- Choose appropriate KG databases/libraries (Neo4j, RDFLib, etc.)
- Design data model for text processing and KG interaction

## Known Challenges
- Authentication security with HMAC-SHA512
- Network reliability for server-dependent features
- Configuration complexity with extensive options
- Styling limitations (no standard CSS)
- Browser compatibility requirements
- Content-type specific features/limitations
- Debugging complexity in client-server model

---

## GitHub Wiki Maintenance

### Wiki Structure
- **Home.md**: Project overview and navigation
- **MyScript-Integration-Guide.md**: SDK setup and configuration
- **Tag-Based-Actions-Implementation.md**: UI design and data model
- **Technical-Architecture.md**: Component diagrams and flows
- **Development-Guide.md**: Environment setup and testing
- **API-Reference.md**: Internal APIs and integration points

### Documentation Standards
- Include last updated date on pages
- Use code blocks with syntax highlighting
- Document API methods with signatures and types
- Use consistent notation for diagrams
- Link between related concepts and external docs

### Critical Details to Document
1. MyScript's client-server architecture
2. UI-based approach to tags (not handwritten recognition)
3. Data model for tag-content associations
4. Network requirements and error handling
5. Configuration options for content types
6. Browser compatibility information

### Update Process
1. Pull latest changes from wiki repository
2. Update markdown files
3. Commit with descriptive message
4. Push changes