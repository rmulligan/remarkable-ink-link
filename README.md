# ✍️ InkLink

**Bring AI to your reMarkable tablet.**  
InkLink connects your reMarkable with powerful AI tooling for handwritten workflows, research, transcription, and task management — all in a calm, focused interface.

> _The Zettelkasten of the Future™ — powered by e-ink and intelligence._

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-brightgreen)
[![DeepSource](https://app.deepsource.com/gh/rmulligan/remarkable-ink-link.svg/?label=active+issues&show_trend=true&token=AtrApop5YKPHPWv1MeAGTR0u)](https://app.deepsource.com/gh/rmulligan/remarkable-ink-link/)
[![DeepSource](https://app.deepsource.com/gh/rmulligan/remarkable-ink-link.svg/?label=code+coverage&show_trend=true&token=AtrApop5YKPHPWv1MeAGTR0u)](https://app.deepsource.com/gh/rmulligan/remarkable-ink-link/)
[![DeepSource](https://app.deepsource.com/gh/rmulligan/remarkable-ink-link.svg/?label=resolved+issues&show_trend=true&token=AtrApop5YKPHPWv1MeAGTR0u)](https://app.deepsource.com/gh/rmulligan/remarkable-ink-link/)

---

## 🚀 What is InkLink?

InkLink is an open-source toolkit that transforms your reMarkable tablet into an AI-augmented thought partner. It bridges paper-like thinking with intelligent workflows — no browser tabs, no distractions.

### ✨ Core Features

- **🧠 AI-Augmented Notes:** Ask questions directly from handwritten notes. Receive structured, editable responses in `.rm` format.
- **🌐 Web-to-Ink Sharing:** Send web content to your tablet and convert it to editable *native ink*, not static text or PDFs. Move, resize, clip, and restructure AI-generated or imported text as if you'd written it by hand.
- **✍️ Claude Vision Handwriting Recognition:** Fast, accurate transcription powered by Claude's vision capabilities, recognizing text directly from handwritten notes without requiring a separate API service.
- **👨‍💻 Claude Code Integration:** AI-powered coding assistance for handwritten pseudocode to code generation, code review, debugging, and technical summaries.
- **🏷️ UI-Based Tag Actions:** Tag content through the user interface and trigger workflows like summarization, calendar integration, and more.
- **📅 Task & Calendar Integration:** Detect tasks in your notes and sync them with your calendar (e.g. Motion, org-agenda).
- **🗂 Smart Indexing:** Generate and maintain table of contents, index pages, and note links using symbols or QR codes.
- **🔌 Modular AI Workflows (MCP-ready):** Supports Multi-Connection Protocol (MCP) for real-time agent communication and toolchain integration.
- **☁️ One-Click reMarkable Setup:** Connect to your reMarkable account with a single click using the "Device Link" flow — no terminal, no token copy-pasting, no dev skills required.
- **🔄 Automatic Sync & Tag-Driven Actions:** Notes sync automatically from your reMarkable. Tags like `#summarize`, `#task`, or `#calendar` trigger AI-powered workflows with no extra steps.
- **🧠 Visual Knowledge Graph:** Automatically generate a personal knowledge graph from your notes — powered by entity recognition, backlinks, and concept clustering.

---

## 📷 Example Use Cases

- Send a web article or AI-generated summary to your reMarkable and edit it as ink — rearrange, clip, highlight, and remix it freely without breaking your writing flow.
- Write a to-do list by hand and sync tasks with your calendar automatically.
- Ask a handwritten question and receive an answer in native ink format — ready to move, rephrase, or expand with a pen.
- Add `#summarize` to a page and get a clean summary beside it, ready to rearrange in ink.
- Use `#task` to automatically extract actionable items from your notes.
- Write `#entity` to identify key concepts for your knowledge graph.
- Sketch pseudocode by hand and use `#code` to generate production-ready code with Claude Code.
- Write handwritten code snippets and use `#review` for AI-powered code review and debugging.
- Explore your evolving thoughts in a live visual knowledge graph powered by your handwriting.

---

## 🛠 Architecture Overview

- Languages: Python + Ruby (CLI + backend utilities)
- One-click Device Link setup via reMarkable Cloud API
- Ink rendering via `drawj2d` to preserve native editing experience
- Handwriting recognition with **Claude Vision** capabilities for direct image-to-text conversion
- Code generation and review with **Claude Code** for technical workflows
- AI orchestration using Flowise, LangChain, or OpenAI APIs
- Modular messaging via MCP (Multi-Connection Protocol)
- Tag-based AI triggers (`#summarize`, `#task`, `#entity`, `#code`, `#review`, etc.)
- Background sync engine with customizable frequency and event-based triggers
- Optional integrations: Emacs/org-roam/org-agenda, Motion, Apple Shortcuts

---

## 📦 Installation

Make sure you have:
- Node.js and Yarn
- Python 3.10 or higher
- Docker and Docker Compose (optional)
- Claude CLI (for handwriting recognition)

To install dependencies and set up the local environment, run:

```bash
yarn
```
After installing, set up Git hooks to enforce formatting and dependency locks:
```bash
pre-commit install
```

This will install Python dependencies via Poetry.

For a barebones local install without Docker:

```bash
poetry install
```

Or with Yarn:

```bash
yarn install:bare
```

To build and start the application in Docker (default):

```bash
yarn install:docker
```

This will build the Docker image and start the container.

### Deploying on a Raspberry Pi

You can deploy InkLink to a remote Raspberry Pi (e.g., Pi 5 running Ubuntu 24) using the provided script:

```bash
chmod +x scripts/deploy_to_pi.sh
scripts/deploy_to_pi.sh
```

This script will:
- SSH into "ryan@100.110.75.57"
- Install Docker and Docker Compose if missing
- Clone or update the InkLink repository in `~/inklink`
- Build the Docker image
- Run the container mapped to port 9999

Ensure your SSH keys are configured for passwordless access.

Once installed, you can:
- Run the app locally: `yarn start`
  
## 🔐 Authentication

Follow these steps to authenticate your reMarkable account:

1. Start the InkLink server (default on port 9999):

   ```bash
   docker-compose up -d inklink
   ```

2. In your browser, visit:

   ```
   http://localhost:9999/auth
   ```

3. On the authentication page:
   • Click the link to go to the reMarkable device connect page and retrieve your one‑time code.  
   • Paste the code into the form and submit.

InkLink will invoke `rmapi login` under the hood and store your credentials. Once authenticated, you can use the `/share` endpoint to upload documents without additional prompts.

- Run tests: `yarn test`
- Lint code: `yarn lint`
- Format code: `yarn format`

For Docker control:
- Build image: `yarn docker:build`
- Start containers: `yarn docker:up`
- Stop containers: `yarn docker:down`

## 📬 Using the Web-to-Ink Endpoint

Currently, the main functionality available is the web-to-ink conversion service. Once the server is running:

1. Send a POST request to the `/share` endpoint with a URL to convert
2. The service will:
   - Generate a QR code linking back to the original content
   - Process the content (supporting both web pages and PDFs)
   - Convert to native reMarkable ink format (.rm)
   - Upload to your reMarkable cloud account

Example using curl:
```bash
curl -X POST http://localhost:9999/share -d '{"url":"https://example.com"}'
```

Or with a simple request containing just the URL:
```bash
curl -X POST http://localhost:9999/share -d "https://example.com"
```

The response will contain success status and a message.

For backward compatibility, the default response is in plain text:
```json
{"success": true, "message": "Webpage uploaded to Remarkable: Example Domain"}
```

If your client includes `Accept: application/json` in the request header, you'll receive a JSON response with a download link:
```json
{
  "success": true,
  "message": "Webpage uploaded to Remarkable: Example Domain",
  "download": "/download/document123.rm"
}
```

### Downloading Generated Documents

You can directly download the converted reMarkable documents using the `/download` endpoint:

```
GET /download/filename.rm
```

This allows you to save and review documents locally without requiring a reMarkable device.

## 📝 Handwriting Recognition with Lilly

InkLink uses Claude Vision capabilities through a personified assistant named "Lilly" that processes handwritten content from your reMarkable tablet.

### Features

- Direct handwriting recognition from `.rm` files
- Special tag processing (`#summarize`, `#task`, `#entity`, etc.)
- Knowledge graph integration
- Personalized responses based on context

### Example Commands

Process a single page:
```bash
python -m inklink.main process path/to/file.rm
```

Process an entire notebook:
```bash
python -m inklink.main process-notebook path/to/notebook/directory
```

See [Claude Vision Integration](docs/integrations/claude-vision/usage.md) for detailed setup and usage instructions.

## 🧑‍💻 Claude Code Integration

InkLink brings powerful AI coding assistance directly to your reMarkable tablet through Claude Code integration. Transform handwritten pseudocode into production-ready code, get AI-powered code reviews, and debug issues — all while maintaining a natural handwriting workflow.

### Features

- **Code Generation**: Transform handwritten pseudocode into functioning code with `#code` tags
- **Code Review**: Get AI-powered feedback on handwritten code snippets with `#review` tags
- **Debugging**: Identify and fix issues in code with `#debug` tags
- **Technical Summaries**: Generate documentation from code or technical notes with `#summary` tags
- **Best Practices**: Learn coding patterns and optimizations with handwritten queries
- **Privacy-Aware**: Intelligent routing keeps sensitive code in your local environment

### Example Workflows

#### Generate code from pseudocode:
```bash
# Write pseudocode in your notebook with #code tag
# Claude Code will generate production-ready implementation
python -m inklink.main cloud-coder --input path/to/pseudocode.rm
```

#### Review existing code:
```bash
# Write or paste code in notebook with #review tag
# Get detailed feedback and suggestions
python -m inklink.main cloud-coder --review path/to/code.rm
```

### Configuration

Add Claude Code CLI settings to your environment:
```bash
# Add to your .env file
CLAUDE_CODE_COMMAND=claude  # Path to Claude CLI
CLAUDE_CODE_MODEL=claude-3-opus-20240229  # Preferred model
CLAUDE_CODE_TIMEOUT=120  # Timeout in seconds
CLAUDE_CODE_MAX_TOKENS=8000  # Max response tokens
```

See [Claude Code Integration Guide](docs/CLAUDE_CODE_INTEGRATION_GUIDE.md) for detailed setup and usage instructions.

---

## 🔌 Integrations

InkLink is built with modularity in mind. Through MCP, it can connect to external tools and services like calendars, research agents, or lifelogging platforms.

Available integrations:
- `GitHub MCP`: Integrated GitHub repository management directly accessible via Claude. See [GitHub Integration](docs/github_integration.md).
- `Knowledge Graph`: A powerful knowledge graph system for entity extraction, relationship mapping, and semantic search across all content types. See documentation in the codebase.
- `Limitless Integration`: Automatic syncing of Limitless Pendant life logs into the knowledge graph for entity extraction, relationship mapping, and semantic search. See [Limitless Integration](docs/limitless_integration.md).
- `Claude Vision`: Handwriting recognition powered by Claude's vision capabilities. See [Claude Vision Integration](docs/integrations/claude-vision/usage.md).
- `Claude Code`: AI-powered coding assistance for code generation, review, and debugging. See [Claude Code Integration Guide](docs/CLAUDE_CODE_INTEGRATION_GUIDE.md).

> Want to build your own? Stay tuned for the `inklink-mcp-template` to roll your own plug-ins.

---

## 🧪 Roadmap

- [x] Core infrastructure and Docker environment setup
- [x] Web-to-ink conversion for articles and webpages
- [x] PDF-to-ink conversion with source linking
- [x] reMarkable Cloud authentication UI
- [x] Service-level Google Docs integration
- [x] Handwriting recognition with Claude Vision capabilities
- [x] Personified AI assistant (Lilly) for processing handwritten content
- [x] Tag-based action system: `#summarize`, `#task`, `#entity`, etc.
- [x] Claude Code integration for AI-powered coding assistance
- [ ] Calendar sync module
- [x] Visual knowledge graph builder
- [x] First MCP integration: Limitless Pendant life log sync
- [ ] Hosted version with user-friendly flows
- [ ] Two-way sync and auto-update

---

## 👥 Community

- Discussions and issue tracking coming soon
- Contributions, integrations, and feedback welcome
- If you're a reMarkable hacker, PKM nerd, or AI tinkerer — you're in the right place

---

## 🪪 License

MIT License — permissive and open.  
You are free to use, modify, extend, and build commercial or personal tools on top of InkLink. We may provide a hosted version in the future, but the core will always remain open and community-driven.

## 🗂 Repository Organization

The repository has been reorganized for improved maintainability and clarity:

```
inklink/
├── docs/               # Project documentation 
├── notebooks/          # Sample reMarkable notebooks
├── scripts/            # Utility and maintenance scripts
├── src/                # Source code
│   └── inklink/        # Main package
│       ├── adapters/   # Integration adapters
│       ├── api/        # API endpoints
│       ├── di/         # Dependency injection
│       ├── services/   # Core services
│       └── utils/      # Helper utilities
├── tests/              # Test suite organized by component
│   ├── adapters/       # Tests for adapters
│   ├── api/            # Tests for API endpoints
│   ├── extraction/     # Tests for content extraction
│   ├── integration/    # End-to-end tests
│   ├── mocks/          # Test mocks and fixtures
│   └── services/       # Tests for services
├── tools/              # Repository maintenance tools
└── web/                # Web interface components
```

### Submodules

This repository includes the following Git submodules:

- `src/models/handwriting_model/deep_scribe_original`: Original DeepScribe handwriting model
- `src/models/handwriting_model/maxio`: MaxIO reMarkable integration library

When cloning the repository, use the `--recursive` flag to also clone submodules:

```bash
git clone --recursive https://github.com/remarkable-ink-link/inklink.git
```

If you've already cloned the repository without submodules:

```bash
git submodule update --init --recursive
```

### Organization Principles

The codebase follows these organization principles:

1. **Separation of Concerns**: Clear separation between adapters (external integrations), services (core business logic), and API layers
2. **Component-based Testing**: Test files are organized by component type for easier maintenance
3. **Documentation-centric**: Comprehensive documentation in the `docs/` directory organized by topic
4. **Modular Design**: Each component is designed to be modular and replaceable

## 💡 Configuration Options

### PDF Rendering Modes

InkLink supports two PDF rendering modes, configurable via the `INKLINK_PDF_RENDER_MODE` environment variable:

- **`raster`** (default): Renders PDFs as rasterized PNG images. More reliable with complex PDFs but lower quality.
- **`outline`**: Embeds vector outlines from PDFs directly. Higher quality but may fail with complex PDFs.

To change the mode:

```bash
# In Docker
docker-compose up -d -e INKLINK_PDF_RENDER_MODE=outline inklink

# Or set in your environment before running
export INKLINK_PDF_RENDER_MODE=outline
yarn start
```

When using `outline` mode, you can also configure:
- `INKLINK_PDF_PAGE`: Which page to render (default: 1)
- `INKLINK_PDF_SCALE`: Scale factor for rendering (default: 1.0)

### Handwriting Recognition

InkLink uses Claude Vision capabilities through the Claude CLI for handwriting recognition.

To configure, add Claude CLI settings to your environment:

```bash
# Add to your .env file
CLAUDE_COMMAND=claude  # Path to Claude CLI if not in PATH
CLAUDE_MODEL=claude-3-opus-20240229  # Your preferred Claude model with vision capabilities
```

See [Claude Vision Integration](docs/integrations/claude-vision/usage.md) for detailed setup instructions.

## 🐞 Troubleshooting

If you encounter an error pulling images such as:

```
failed to solve: python:3.10-slim: error getting credentials - err: exec: "docker-credential-desktop.exe": executable file not found in $PATH, out: ``
```

open your Docker client configuration file (`~/.docker/config.json`) and remove or disable any `credsStore` or `credHelpers` entries referencing Windows credential helpers. For example:

```json
{
  // …
  // "credsStore": "desktop.exe",
  // "credHelpers": { … }
}
```

Save the file and rerun `docker compose build`.

---

## 🧠 Created by

Ryan Mulligan – [@rmulligan](https://github.com/rmulligan)  
Senior Software Engineer • Musician • Workflow Optimizer  
Proudly crafting the Zettelkasten of the Future™.
## API: /ingest Endpoint

**POST /ingest**

Ingest content from browser extension, Siri shortcut, or web UI.

**Request Body (application/json):**
- `type`: `"web"`, `"note"`, `"shortcut"`, etc. (string, required)
- `title`: Title of the content (string, required)
- `content`: Main content (text, HTML, markdown, etc., required)
- `metadata`: Optional dictionary (e.g., `source_url`, `tags`, etc.)

**Example:**
```json
{
  "type": "web",
  "title": "Interesting Article",
  "content": "<h1>Example</h1><p>Some content...</p>",
  "metadata": {
    "source_url": "https://example.com",
    "tags": ["reading", "reference"]
  }
}
```

**Response:**
- `{"status": "accepted"}` on success
- `{"error": "...error message..."}` on failure

See API_DOCS.md for full details.