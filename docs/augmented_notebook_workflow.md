# Augmented Notebook Workflow

This document describes the integrated workflow for processing reMarkable notebook pages with AI analysis, knowledge graph integration, and response generation.

## Overview

The augmented notebook workflow enables a seamless integration between handwritten notes on reMarkable tablets, AI processing with Claude, knowledge graph storage, and automatic response generation. This creates a powerful system for note-taking, research, and knowledge management.

The workflow consists of these key steps:

1. **Handwriting Recognition**: Convert handwritten notes to digital text
2. **Tag & Request Analysis**: Identify special tags and user requests in the content
3. **Knowledge Extraction**: Extract entities and relationships to the knowledge graph
4. **AI Processing**: Process content through Claude with context from the knowledge graph
5. **Response Generation**: Generate helpful responses to user queries
6. **Knowledge Categorization**: Categorize all correspondence in the knowledge graph
7. **Response Conversion**: Convert responses back to ink format
8. **Notebook Appending**: Append the responses directly to the notebook

## System Architecture

The augmented notebook workflow integrates multiple components:

```
┌─────────────────┐     ┌────────────────────┐     ┌─────────────────────┐
│  reMarkable     │────▶│  Handwriting       │────▶│  Tag & Request      │
│  Notebook Pages │     │  Recognition       │     │  Analysis           │
└─────────────────┘     └────────────────────┘     └──────────┬──────────┘
                                                              │
                                                              ▼
┌─────────────────┐     ┌────────────────────┐     ┌─────────────────────┐
│  Notebook       │◀────│  Response          │◀────│  AI Processing with │
│  Appending      │     │  Conversion        │     │  Claude Code        │
└─────────────────┘     └────────────────────┘     └──────────┬──────────┘
                                                              │
                          ┌───────────────────────────────────┘
                          │
┌─────────────────┐     ┌▼───────────────────┐     ┌─────────────────────┐
│  Web Search     │────▶│  Knowledge Graph    │◀────│  Knowledge          │
│  Integration    │     │  (Neo4j)            │     │  Extraction         │
└─────────────────┘     └────────────────────┘     └─────────────────────┘
```

## Key Features

### Tag-Based Actions

The system recognizes special tags in the user's handwritten notes that trigger specific actions:

| Tag                         | Description                                      |
|-----------------------------|--------------------------------------------------|
| `#tool:search`              | Trigger web search for relevant information      |
| `#tool:kg:add`              | Add entities and relationships to knowledge graph|
| `#tool:kg:query`            | Query the knowledge graph for information        |
| `#tool:kg:visualize`        | Generate visualization of knowledge graph        |
| `#personal`                 | Mark content as personal (not categorized)       |
| `#tag:<category>`           | Categorize the note under a specific category    |

### GPU-Accelerated Knowledge Processing

The knowledge extraction pipeline uses GPU acceleration for high-performance processing:

- **Entity Recognition**: Using spaCy with GPU acceleration
- **Semantic Embeddings**: Using sentence-transformers with CUDA support  
- **Vector Search**: Using FAISS-GPU for nearest neighbor search
- **Local Processing**: All processing happens locally for privacy

### Integrated Context

The AI processing incorporates multiple sources of context:

1. **Note Content**: The recognized text from the handwritten note
2. **Knowledge Graph**: Entities and relationships relevant to the query
3. **Web Search**: Up-to-date information from the web when relevant
4. **Previous Conversations**: History of interactions on the same topic
5. **Document Metadata**: Information about the notebook and page

### Response Appending

Responses are automatically converted back to reMarkable ink format and appended to the notebook:

- **Clean Formatting**: Structured with headings, lists, and sections
- **Source Citations**: References to information sources
- **Visualization Integration**: Knowledge graph visualizations when requested
- **Seamless Experience**: Appears directly in the notebook for immediate use

## Using the Augmented Notebook Workflow

### Processing Pages

To process a notebook page through the workflow:

```python
from inklink.services.augmented_notebook_service import AugmentedNotebookService

service = AugmentedNotebookService()
success, result = service.process_notebook_page('/path/to/notebook_page.rm')

if success:
    print(f"Recognized text: {result['recognized_text']}")
    print(f"Generated response: {result['claude_processing']['response']}")
```

### HTTP Endpoints

The workflow is accessible through HTTP endpoints:

```
POST /notebooks/process
{
    "file_path": "/path/to/notebook_page.rm",
    "append_response": true,
    "extract_knowledge": true,
    "categorize_correspondence": true
}
```

### Batch Processing

Multiple pages can be processed in batch:

```
POST /notebooks/batch_process
{
    "file_paths": [
        "/path/to/page1.rm",
        "/path/to/page2.rm",
        "/path/to/page3.rm"
    ],
    "append_response": true
}
```

### MCP Integration for Claude

The workflow is available to Claude and other assistants via MCP tools:

- `process_notebook_page`: Process a single notebook page
- `batch_process_notebook_pages`: Process multiple pages in batch

## Example Use Cases

### Research Workflow

1. Take handwritten notes on research papers
2. Tag with `#tool:kg:add` to extract knowledge
3. Ask questions like "What are the connections between these concepts?"
4. Receive AI responses with insights from the knowledge graph
5. Continue taking notes with new insights

### Study Assistant

1. Write notes and questions in a notebook with `#tool:search`
2. Automatically receive explanations, examples, and references
3. Knowledge is categorized for future reference
4. Follow-up with additional questions on the same page
5. Build a comprehensive knowledge base over time

### Personal Knowledge Management

1. Write thoughts, ideas, and questions in notebooks
2. Tag with categories like `#project:name` or `#area:topic`
3. Cross-reference information with the knowledge graph
4. Discover unexpected connections between ideas
5. Generate summaries and insights from your notes

## Configuration Options

The augmented notebook workflow can be configured via environment variables or API:

```
GET /notebooks/config
```

```
PUT /notebooks/config
{
    "tag_processing": true,
    "web_search_enabled": true,
    "kg_search_enabled": true,
    "claude_model": "claude-3-5-sonnet",
    "min_semantic_similarity": 0.6
}
```

## Implementation Details

The workflow is implemented through these key components:

1. **AugmentedNotebookService**: Core service managing the workflow
2. **AugmentedNotebookController**: HTTP controller for web access
3. **AugmentedNotebookMCPIntegration**: MCP integration for AI assistants

## Privacy and Security

The implementation prioritizes privacy and security:

- **Local Processing**: All handwriting recognition happens locally
- **Private Knowledge Graph**: Knowledge is stored in a private Neo4j database
- **Configurable Web Access**: Web search can be disabled
- **Tag-Based Privacy**: Content can be marked private with tags
- **No Cloud Dependency**: Works completely offline if needed

## Future Enhancements

Planned enhancements to the workflow include:

1. **Multi-Page Processing**: Process entire notebooks with cross-page context
2. **Diagram Recognition**: Extract structured data from handwritten diagrams
3. **Interactive References**: Create clickable references between pages
4. **Collaborative Knowledge**: Share knowledge graphs between users
5. **Template System**: Create custom templates for specific workflows