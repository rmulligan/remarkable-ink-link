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
- **🌐 Web-to-Ink Sharing:** Send web content to your tablet as ink-friendly pages, perfect for annotation and long-form reading.
- **✍️ Handwriting Transcription:** Automatically convert handwritten content into structured text using OCR + NLP.
- **📅 Task & Calendar Integration:** Detect tasks in your notes and sync them with your calendar (e.g. Motion, org-agenda).
- **🗂 Smart Indexing:** Generate and maintain table of contents, index pages, and note links using symbols or QR codes.
- **🔌 Modular AI Workflows with MCP:** Supports Multi-Connection Protocol (MCP) for real-time agent communication and modular toolchains. Swap in your favorite AI, planner, or search tools with minimal config.

---

## 📷 Example Use Cases

- Annotate a shared web article and get a summary, follow-up research, or counterpoints delivered to your notebook.
- Write a to-do list by hand, and watch it populate your digital planner or calendar.
- Brainstorm song lyrics or code ideas and send them to an LLM for creative or technical assistance — all from e-ink.

---

## 🛠 Architecture Overview

- Languages: Python + Ruby (CLI + backend utilities)
- reMarkable Cloud API / `rmapi` for syncing
- Handwriting recognition via MyScript or Tesseract
- AI orchestration with Flowise, LangChain, or OpenAI APIs
- Modular messaging via [MCP](https://github.com/multiprocess-protocol/mcp) for dynamic tool integration
- Optional integrations: Emacs (org-roam/org-agenda), Motion, Apple Shortcuts, Drafts, etc.

---

## 📦 Installation

_(Early alpha — setup guide coming soon!)_

Expected modules:
- CLI tools to send and receive `.rm` pages
- Local server or hosted agent for AI processing
- MCP-based messaging layer for extensibility
- Optional sync to calendars and org-mode agenda views

---

## 🔌 Extending with MCP

InkLink uses the [Multi-Connection Protocol (MCP)](https://github.com/multiprocess-protocol/mcp) to support real-time, modular interactions between note events and intelligent services.

This means you can:
- Plug in your own AI agent (local or cloud-based)
- Route structured data to/from org-mode, Motion, or other tools
- Add handlers for QR code-based triggers, search requests, or task capture
- Interact with InkLink from Emacs, a terminal app, or mobile-friendly tools

MCP makes InkLink behave like a brainstem — you bring the neurons.

---

## 🧪 Roadmap

- [ ] MVP: AI question/answer roundtrip via `.rm` files
- [ ] Web-to-ink article parser and converter
- [ ] NLP: handwriting transcription + entity/tag extraction
- [ ] Task & calendar module with auto-sync
- [ ] Live TOC/index generator with backreference linking
- [ ] Optional hosted platform with API hooks

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

Ryan Mulligan – [@mulligan](https://github.com/mulligan)  
Senior Software Engineer • Musician • Workflow Optimizer  
Proudly crafting the Zettelkasten of the Future™.
