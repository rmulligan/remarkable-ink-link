# ✍️ InkLink

**Bring AI to your reMarkable tablet.**  
InkLink connects your reMarkable with powerful AI tooling for handwritten workflows, research, transcription, and task management — all in a calm, focused interface.

> _The Zettelkasten of the Future™ — powered by e-ink and intelligence._

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-brightgreen)

---

## 🚀 What is InkLink?

InkLink is an open-source toolkit that transforms your reMarkable tablet into an AI-augmented thought partner. It bridges paper-like thinking with intelligent workflows — no browser tabs, no distractions.

### ✨ Core Features

- **🧠 AI-Augmented Notes:** Ask questions directly from handwritten notes. Receive structured, editable responses in `.rm` format.
- **🌐 Web-to-Ink Sharing:** Send web content to your tablet and convert it to editable *native ink*, not static text or PDFs. Move, resize, clip, and restructure AI-generated or imported text as if you'd written it by hand.
- **✍️ Hybrid Handwriting Recognition:** Fast, accurate transcription powered by MyScript, with optional verification using local vision models for improved accuracy.
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
- Add `#summarize` to a dense page and get a clean summary beside it, ready to rearrange in ink.
- Use `#calendar` in a note and have appointments sync to your external calendar.
- Explore your evolving thoughts in a live visual knowledge graph powered by your handwriting.

---

## 🛠 Architecture Overview

- Languages: Python + Ruby (CLI + backend utilities)
- One-click Device Link setup via reMarkable Cloud API
- Ink rendering via `drawj2d` to preserve native editing experience
- Handwriting recognition with **MyScript** (primary), plus optional **vision model verification**
- AI orchestration using Flowise, LangChain, or OpenAI APIs
- Modular messaging via MCP (Multi-Connection Protocol)
- Tag-based AI triggers (`#summarize`, `#calendar`, `#index`, etc.)
- Background sync engine with customizable frequency and event-based triggers
- Optional integrations: Emacs/org-roam/org-agenda, Motion, Apple Shortcuts

---

## 📦 Installation

Make sure you have:
- Node.js and Yarn
- Python 3.10 or higher
- Docker and Docker Compose (optional)

To install dependencies and set up the local environment, run:

```bash
yarn
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

Once installed, you can:
- Run the app locally: `yarn start`
  
## 🔐 Authentication

Set up reMarkable Cloud pairing and auto configure rmapi using the ddvk fork:
```bash
# Start the authentication UI (default at http://127.0.0.1:8000/auth)
yarn auth
```
Open the auth page in your browser, enter your reMarkable credentials, and click Connect. InkLink will invoke `rmapi config` under the hood to store your credentials.

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

The response will contain success status and a message:
```json
{"success": true, "message": "Webpage uploaded to Remarkable: Example Domain"}
```

---

## 🔌 Integrations

InkLink is built with modularity in mind. Through MCP, it can connect to external tools and services like calendars, research agents, or lifelogging platforms.

Standalone integration modules (coming soon):
- `inklink-mcp-limitless`: Sync lifelog entries from the Limitless Pendant and convert them into editable ink for review, summarization, or planning.

> Want to build your own? Stay tuned for the `inklink-mcp-template` to roll your own plug-ins.

---

## 🧪 Roadmap

- [x] Core infrastructure and Docker environment setup
- [x] Web-to-ink conversion for articles and webpages  
- [x] PDF-to-ink conversion with source linking
- [x] reMarkable Cloud authentication UI
- [ ] AI Q&A roundtrip via `.rm` files
- [ ] Handwriting recognition (MyScript Cloud integration)
- [ ] Tag-based automation: `#summarize`, `#calendar`, `#index`, etc.
- [ ] Calendar sync module
- [ ] Visual knowledge graph builder
- [ ] Hosted version with user-friendly flows
- [ ] Two-way sync and auto-update
- [ ] First MCP integration: Limitless Pendant

---

## 👥 Community

- Discussions and issue tracking coming soon
- Contributions, integrations, and feedback welcome
- If you're a reMarkable hacker, PKM nerd, or AI tinkerer — you're in the right place

---

## 🪪 License

MIT License — permissive and open.  
You are free to use, modify, extend, and build commercial or personal tools on top of InkLink. We may provide a hosted version in the future, but the core will always remain open and community-driven.

---

## 🧠 Created by

Ryan Mulligan – [@rmulligan](https://github.com/rmulligan)  
Senior Software Engineer • Musician • Workflow Optimizer  
Proudly crafting the Zettelkasten of the Future™.