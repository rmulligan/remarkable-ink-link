# Codex Project Guide: InkLink

This repo is for InkLink — a toolkit that enables users to interact with AI directly from their reMarkable tablet.

Primary project goals:
- Convert AI and web responses into editable ink layers (.rm files)
- Allow tagging of pages to trigger workflows (e.g., #summarize, #calendar)
- Enable automatic sync to/from reMarkable via `rmapi`
- Support modular AI tool interaction via MCP

Important repo structure:
- `scripts/` → CLI tools for syncing, formatting, task extraction, etc.
- `formatters/` → drawj2d-compatible layout generators
- `handlers/` → AI-triggered tools (summarizers, entity extractors, calendar sync, etc.)
- `config/` → MCP tool definitions and user preferences

Dev Notes:
- Codex can use the ddvk fork of `rmapi` located at `~/Projects/rmapi`
- Target `.rm` file generation from markdown or text output
- Use prompt-based generation of HCL layout where needed
- If CLI scaffolding is needed, make it cross-platform where possible (macOS + Linux)

Style Guidelines:
- Be modular and testable
- Favor `stdin`/`stdout` communication where possible (MCP-friendly)
- If AI responses are generated, format for reMarkable-appropriate layout and readability
