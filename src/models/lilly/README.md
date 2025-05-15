# Lilly: reMarkable Ink Link Assistant

Lilly is your thoughtful assistant for working with reMarkable tablet handwritten notes. She uses Claude's vision capabilities to understand handwritten content and helps you organize your thoughts, ideas, and knowledge.

## 🚀 Getting Started

To start a conversation with Lilly, run:

```bash
./start_lilly.sh
```

This will initialize Lilly's knowledge graph and start the Claude terminal interface with Lilly's persona and configuration.

## 🔍 Core Features

- **Handwriting Recognition**: Process handwritten notes from your reMarkable tablet
- **Knowledge Extraction**: Identify key concepts, entities, and relationships
- **Task Management**: Recognize and track tasks from your notes
- **Note Organization**: Connect and structure your handwritten content
- **Research Support**: Develop ideas and explore concepts further

## 🛠️ Available Tools

Lilly comes with several useful tools in the `tools/` directory:

### 📝 Process Handwriting

Process rendered pages from your reMarkable tablet:

```bash
./tools/process_handwriting.py /path/to/image.png --content-type mixed --kg
```

Options:
- `--content-type`: Type of content (text, math, diagram, mixed)
- `--output`: Path to save transcription
- `--kg`: Save extracted entities and relationships to knowledge graph

### 🔄 Sync reMarkable

Sync and process notebooks from your reMarkable tablet:

```bash
# List available notebooks
./tools/sync_remarkable.py --list

# Sync a specific notebook
./tools/sync_remarkable.py --notebook [notebook-id] --process

# Sync all notebooks
./tools/sync_remarkable.py --process
```

### 🧠 Knowledge Graph

Initialize Lilly's knowledge graph:

```bash
./tools/initialize_knowledge_graph.py
```

## 🗂️ Directory Structure

```
lilly/
├── config/                     # Configuration files
│   ├── lilly_config.json       # Main configuration
│   └── lilly_persona.md        # Lilly's personality and instructions
├── memories/                   # Long-term memory storage
├── tools/                      # Helper scripts and utilities
│   ├── initialize_knowledge_graph.py
│   ├── process_handwriting.py
│   └── sync_remarkable.py
├── workspace/                  # Active working directory
│   └── remarkable_sync/        # Synced reMarkable content
├── README.md                   # This file
└── start_lilly.sh              # Startup script
```

## 💬 Example Interactions

- "Please process this handwritten note I just scanned"
- "Extract key concepts from my notebook on machine learning"
- "What tasks did I write down in yesterday's meeting notes?"
- "Show me all entities related to 'project management' in my notes"
- "Help me organize these scattered thoughts into a coherent structure"
- "Find connections between these concepts across my notebooks"

## 🧩 MCP Integration

Lilly leverages Claude's MCP (Multi-Connection Protocol) tools for enhanced functionality:

- **Knowledge Graph**: Uses neo4j-knowledge MCP tool to store and query structured information
- **Memory Bank**: Allows storing and retrieving persistent memories 
- **Task Management**: Helps track and manage tasks identified in your notes

## 📋 Requirements

- Claude terminal command installed and configured
- MCP tools enabled in Claude
- Python 3.8+ with required packages
- reMarkable API tools (rmapi) for synchronization
- Page rendering tools (rmscene or drawj2d) for visualization

## 🔧 Customization

You can customize Lilly's behavior and persona by editing:

- `config/lilly_config.json` - General configuration settings
- `config/lilly_persona.md` - Lilly's personality and interaction style

## 🔮 Future Enhancements

- Integration with Limitless life log for contextual awareness
- Advanced handwriting diagram recognition
- Automated notebook organization suggestions
- Semantic search across handwritten content
- Enhanced task and project management