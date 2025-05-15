# Lilly Tool Usage Guide

This document serves as a memory for Lilly about how to use both the built-in Claude MCP tools and custom project-specific tools.

## Built-in Claude MCP Tools

Claude has several built-in MCP tools that Lilly can leverage directly:

### 1. Neo4j Knowledge Graph

The `neo4j-knowledge` tool provides direct access to graph database functionality:

```
# List all available entities
mcp__neo4j-knowledge__list_entities

# Search for nodes related to a topic
mcp__neo4j-knowledge__search_nodes({"query": "project management"})

# Create new entities
mcp__neo4j-knowledge__create_entities({
  "entities": [
    {
      "name": "Meeting Notes",
      "entityType": "Note",
      "observations": ["Contains action items from weekly standup"]
    }
  ]
})

# Create relationships between entities
mcp__neo4j-knowledge__create_relations({
  "relations": [
    {
      "from": "Meeting Notes",
      "relationType": "MENTIONS",
      "to": "Project Timeline"
    }
  ]
})

# Switch to Lilly's database
mcp__neo4j-knowledge__switch_database({"databaseName": "lilly_knowledge", "createIfNotExists": true})
```

### 2. Memory Bank

The memory bank tool allows for storing and retrieving structured information:

```
# List available projects
mcp__memory-bank-mcp__list_projects

# Read a specific memory
mcp__memory-bank-mcp__memory_bank_read({
  "projectName": "lilly",
  "fileName": "remarkable_workflows.md"
})

# Write a new memory
mcp__memory-bank-mcp__memory_bank_write({
  "projectName": "lilly",
  "fileName": "meeting_summaries.md",
  "content": "# Meeting Summaries\n\n..."
})

# Update an existing memory
mcp__memory-bank-mcp__memory_bank_update({
  "projectName": "lilly",
  "fileName": "remarkable_workflows.md",
  "content": "Updated content..."
})
```

### 3. Task Management

The tasks MCP tool allows tracking and managing tasks:

```
# Create a new task request
mcp__tasks-mcp__request_planning({
  "originalRequest": "Process handwritten notes from today's meeting",
  "tasks": [
    {
      "title": "Sync notebook from reMarkable",
      "description": "Download the latest meeting notes notebook from reMarkable cloud"
    },
    {
      "title": "Process handwritten content",
      "description": "Use Claude vision to extract text and entities from meeting pages"
    },
    {
      "title": "Update knowledge graph",
      "description": "Add extracted entities and relationships to knowledge graph"
    }
  ]
})

# Get the next pending task
mcp__tasks-mcp__get_next_task({"requestId": "req-123"})

# Mark a task as completed
mcp__tasks-mcp__mark_task_done({
  "requestId": "req-123",
  "taskId": "task-1",
  "completedDetails": "Successfully synced notebook 'Meeting Notes'"
})
```

## Custom Project Tools

In addition to Claude's built-in MCP tools, Lilly has access to custom tools specifically designed for reMarkable integration:

### 1. Handwriting Processing

The handwriting processing tool can be invoked directly from the terminal:

```bash
# Process a single handwritten page
./tools/process_handwriting.py /path/to/image.png --content-type mixed --kg

# Using specific content type for math notes
./tools/process_handwriting.py /path/to/math_notes.png --content-type math --kg

# Process without adding to knowledge graph
./tools/process_handwriting.py /path/to/image.png --output transcription.txt
```

When using Claude, you can guide the user to run these commands or use the following approach to describe what you're doing:

```
I'll process your handwritten note using Claude's vision capabilities to extract text, 
identify key concepts, and add them to your knowledge graph. You can run this command:

./lilly/tools/process_handwriting.py /path/to/your/note.png --content-type mixed --kg
```

### 2. reMarkable Sync

For syncing reMarkable notebooks, use:

```bash
# List available notebooks
./tools/sync_remarkable.py --list

# Sync and process a specific notebook
./tools/sync_remarkable.py --notebook [notebook-id] --process

# Sync all notebooks
./tools/sync_remarkable.py --process
```

When using Claude, you can instruct the user to run these commands or describe the process:

```
To sync your latest reMarkable notebooks and process them automatically, you can run:

./lilly/tools/sync_remarkable.py --process

This will download all your notebooks, render the pages, and extract the content using 
Claude's vision capabilities.
```

### 3. Knowledge Graph Integration

For knowledge graph operations specific to Lilly's implementation:

```bash
# Initialize the knowledge graph structure
./tools/initialize_knowledge_graph.py

# Using neo4j-knowledge MCP commands to interact with the graph
# (See Built-in Neo4j Knowledge Graph section above)
```

## Tool Combination Workflows

Here are some effective combinations of tools for common workflows:

### Notebook Processing Workflow

1. Sync a notebook from reMarkable:
   ```bash
   ./tools/sync_remarkable.py --notebook [notebook-id]
   ```

2. Process the synced pages:
   ```bash
   ./tools/process_handwriting.py /path/to/rendered/page.png --kg
   ```

3. Query the knowledge graph for extracted entities:
   ```
   Using the neo4j-knowledge MCP tool, search for entities related to the notebook.
   ```

### Task Extraction Workflow

1. Process a page containing tasks:
   ```bash
   ./tools/process_handwriting.py /path/to/tasks.png --content-type text --kg
   ```

2. Use the knowledge graph to find task entities:
   ```
   Using the neo4j-knowledge MCP tool, search for entities with type "Task"
   ```

3. Create formal tasks in the task management system:
   ```
   Using the tasks-mcp tool, create new tasks based on the extracted information
   ```

## Best Practices

1. **Database Management**:
   - Always ensure you're using the correct knowledge graph database with `mcp__neo4j-knowledge__switch_database`
   - Keep entities and relationships consistent with defined types

2. **Memory Usage**:
   - Store reusable workflows in the memory bank
   - Reference past interactions and notebooks from memory when relevant

3. **Content Type Selection**:
   - Use the appropriate content type when processing handwritten notes:
     - `text` - For regular handwritten text
     - `math` - For mathematical equations and expressions
     - `diagram` - For sketches, diagrams, flowcharts
     - `mixed` - For pages containing a mix of content types

4. **Error Handling**:
   - If a tool fails, suggest alternative approaches
   - For vision processing failures, recommend trying with different content type settings