# InkLink Project Developer Briefing
**April 2025**

## Project Overview

InkLink is an open-source toolkit designed to transform reMarkable tablets into AI-augmented thought partners. The project aims to bridge paper-like thinking with intelligent workflows, providing features like AI-augmented notes, web-to-ink sharing, handwriting recognition, task management, and knowledge graph generation - all without the distractions of browser tabs.

## Current Implementation Status

### Completed Features
- Web-to-ink sharing endpoint for converting web content to reMarkable-compatible format
- PDF processing for downloading and converting PDFs to editable ink format
- QR code generation linking back to original content
- Authentication UI for reMarkable Cloud
- Docker environment with required dependencies
- CI/CD workflow for linting, testing, and building Docker images

### Core Architecture
- Backend built with Python
- FastAPI for the authentication UI
- Custom HTTP server for the main sharing endpoint
- Conversion pipeline utilizing drawj2d for native .rm file generation
- Integration with the ddvk fork of rmapi for reMarkable Cloud connectivity

## User Notes System Context

The user employs a sophisticated note-taking system that combines:
- Digital Zettelkasten principles 
- Bullet journaling techniques
- Daily task scheduling
- Freeform notes on a PDF planner

### Symbol System
- **Empty circle**: Incomplete task
- **Circle with horizontal line**: Task moved forward one day
- **Circle with vertical line**: Task moved to future date
- **Filled circle**: Completed task
- **Chevron/dash**: Note or context for a heading
- **Thicker pen stroke**: Headings
- **Dashed line**: Separator for entries ("settles")
- **Vertical dashed line**: Content grouping for broader topics
- **Margin identifiers**: Cross-references to other pages

This system leverages the reMarkable's unique capability to move ink content around, using a forever-scrolling page that can be expanded as needed.

## Desired AI Features

The user specifically wants InkLink to:

1. **Digest Individual Entries**: Process note content for meaning and context
2. **Knowledge Graph Integration**: Incorporate notes into a broader knowledge system
3. **Index Page Management**: Update index pages automatically
4. **Cross-References**: Maintain references between related content
5. **Task Automation**: Perform actions based on note content and tags
6. **Content Organization**: Help structure and organize accumulated notes

## Technology Stack Decisions

### 1. AI Processing Strategy - Hybrid Approach

We will implement a hybrid approach combining MyScript's specialized handwriting recognition with local Ollama models:

#### MyScript for Primary Handwriting Transcription
- MyScript excels at converting handwriting to text with high accuracy
- Purpose-built for handwriting recognition with years of specialized development
- Handles different handwriting styles effectively

#### Local Ollama Models for Verification and Enhancement
- Use vision-capable models to verify MyScript outputs
- Handle symbol recognition that MyScript might not specialize in
- Perform semantic understanding of content

#### Two-Stage Recognition Pipeline
```
Handwritten Content → MyScript OCR → Ollama Vision Model Verification → Final Output
```

### 2. Recommended Local Models via Ollama

For your RTX 4090 setup with 64GB RAM, we recommend:

#### Primary Models for Tool Calling
- **Llama 3.1 (8B)** - Officially supported by Ollama's tool calling API
- **Dolphin 3.0 Llama 3.1 (8B)** - Specifically designed for function calling capabilities 
- **DeepSeek-R1 Models** - Excellent for reasoning tasks

#### For Vision Tasks (Symbol Recognition)
- **LLaVA 1.5 (7B or 13B)** - Good balance of performance and resource usage
- **Phi-3-Vision** - Excellent balance of size and capability (if available on Ollama)

#### For Knowledge Graph and Semantic Understanding
- **Llama 3 8B** - Good at entity extraction and relationship identification
- **Mistral 7B Instruct** - Strong reasoning capabilities for relationship mapping

### 3. Knowledge Graph with Neo4j

Neo4j is confirmed as our graph database of choice with these integration approaches:

#### LLM Knowledge Graph Builder
- Neo4j's tool for turning unstructured text into a knowledge graph
- Supports multiple LLM providers including open-source models via Ollama
- Ideal for initial knowledge graph construction from notes

#### LangChain + Neo4j Integration
- Provides direct Neo4j integration with natural language interface
- Enables querying knowledge graph in natural language
- Supports task tracking and relationship discovery

#### Graph Schema Design
- **Nodes**: Notes, Tasks, Concepts, References
- **Relationships**: CONTAINS, REFERENCES, EXTENDS, PART_OF
- **Properties**: Task states, timestamps, positions

## Implementation Architecture

### 1. Core Components

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Handwriting    │────▶│ Symbol & Entity │────▶│  Knowledge      │
│  Recognition    │     │  Understanding  │     │  Graph Builder  │
│  (MyScript)     │     │  (Ollama)       │     │  (Neo4j)        │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                      │                       │
         │                      │                       │
         ▼                      ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                 InkLink Orchestration Layer                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
         │                      │                       │
         │                      │                       │
         ▼                      ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Task & Tag    │     │  Index & Ref    │     │  Retrieval      │
│   Processor     │     │  Generator      │     │  Interface      │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 2. Data Flow

1. **Input Processing**:
   - Handwritten notes captured via reMarkable
   - Notes synced to processing server
   - Initial conversion via MyScript API

2. **Symbol and Structure Recognition**:
   - Vision-capable models detect symbols and spatial relationships
   - Task symbols identified and classified
   - Text content associated with relevant symbols

3. **Knowledge Graph Construction**:
   - Entities extracted and added to Neo4j
   - Relationships established between entities
   - Tasks tracked with state information
   - Cross-references mapped to establish connections

4. **Application Features**:
   - Task management based on symbol states
   - Index pages auto-generated from knowledge graph
   - References maintained and updated
   - Content organized based on structure

## LLM Tool Calling Implementation

### 1. Tool Definitions

We will implement tool definitions for these core functions:

```python
SYMBOL_DETECTION_TOOL = {
    'type': 'function',
    'function': {
        'name': 'detect_symbols',
        'description': 'Detect symbols and their meanings in a note',
        'parameters': {
            'type': 'object',
            'properties': {
                'symbols': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'type': {'type': 'string'},
                            'position': {'type': 'object'},
                            'associated_text': {'type': 'string'},
                            'state': {'type': 'string'}
                        }
                    }
                }
            }
        }
    }
}

KNOWLEDGE_GRAPH_TOOL = {
    'type': 'function',
    'function': {
        'name': 'update_knowledge_graph',
        'description': 'Update knowledge graph with entities and relationships',
        'parameters': {
            'type': 'object',
            'properties': {
                'entities': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'type': {'type': 'string'},
                            'content': {'type': 'string'},
                            'metadata': {'type': 'object'}
                        }
                    }
                },
                'relationships': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'source': {'type': 'string'},
                            'target': {'type': 'string'},
                            'type': {'type': 'string'},
                            'properties': {'type': 'object'}
                        }
                    }
                }
            }
        }
    }
}
```

### 2. Tool Calling Integration with Ollama

```python
import ollama

class SymbolDetector:
    def __init__(self, model_name="llama3.1"):
        self.model_name = model_name
        
    def detect_symbols(self, image_data, text_content):
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {
                    'role': 'system', 
                    'content': 'You are an expert at identifying symbols in handwritten notes.'
                },
                {
                    'role': 'user', 
                    'content': f'Analyze this note and identify all symbols: {text_content}'
                }
            ],
            tools=[SYMBOL_DETECTION_TOOL]
        )
        
        return response['message']['tool_calls']
```

### 3. Neo4j Integration

```python
from neo4j import GraphDatabase

class KnowledgeGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def create_entity(self, entity_id, entity_type, content, metadata={}):
        with self.driver.session() as session:
            session.run(
                """
                CREATE (e:Entity {id: $id, type: $type, content: $content, metadata: $metadata})
                """, 
                id=entity_id, 
                type=entity_type, 
                content=content,
                metadata=metadata
            )
            
    def create_relationship(self, source_id, target_id, rel_type, properties={}):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (source:Entity {id: $source_id})
                MATCH (target:Entity {id: $target_id})
                CREATE (source)-[r:RELATIONSHIP {type: $rel_type, properties: $properties}]->(target)
                """,
                source_id=source_id,
                target_id=target_id,
                rel_type=rel_type,
                properties=properties
            )
```

## Development Roadmap

### Phase 1: Core Infrastructure (1-2 Weeks)
- Set up Ollama with selected models
- Implement MyScript integration
- Configure Neo4j database and schema
- Build basic orchestration layer

### Phase 2: Symbol Recognition System (2-3 Weeks)
- Develop symbol recognition pipeline
- Implement verification system between MyScript and Ollama models
- Create spatial relationship detection
- Build symbol-to-meaning mapping

### Phase 3: Knowledge Graph Construction (3-4 Weeks)
- Implement entity extraction
- Build relationship mapping system
- Create graph population algorithm
- Develop task tracking system

### Phase 4: User-Facing Features (3-4 Weeks)
- Implement index page generation
- Build cross-reference system
- Create task management interface
- Develop content organization tools

### Phase 5: Testing and Refinement (2-3 Weeks)
- Conduct performance testing
- Optimize model usage
- Refine graph queries
- Improve accuracy of symbol detection

## Outstanding Issues to Address

### High Priority
- Missing test for plain text input with mixed valid/invalid content (#21)

### Medium Priority
- Code quality issues requiring attention (#31, #27)
- Need to refactor complex methods including:
  - `_upload_with_n_flag` method in RemarkableService (#22)
  - HTML parsing logic in GoogleDocsService and WebScraperService (#23)
  - Long content loops in `create_hcl` method (#36, #38)

### Low Priority
- Multiple code quality issues like:
  - Extracting duplicate code into functions (#34, #42)
  - Avoiding conditionals in tests (#25, #24, #41)
  - Using named expressions to simplify assignment and conditionals (#26, #30, #39)

## Next Steps for Development Team

1. **Environment Setup**
   - Install Ollama and configure selected models
   - Set up Neo4j database instance
   - Configure MyScript API access

2. **Model Evaluation**
   - Test recommended models on sample handwritten notes
   - Benchmark performance on symbol recognition tasks
   - Evaluate tool calling capabilities

3. **Prototype Development**
   - Build MVP of the hybrid recognition pipeline
   - Implement basic Neo4j integration
   - Create test suite for accuracy validation

4. **Documentation**
   - Update API documentation
   - Create detailed environment setup guide
   - Document model configuration options

## Resources and References

- [Ollama Tool Support Documentation](https://ollama.com/blog/tool-support)
- [Neo4j LLM Knowledge Graph Builder](https://neo4j.com/labs/genai-ecosystem/llm-graph-builder/)
- [LangChain Ollama Integration](https://js.langchain.com/docs/integrations/chat/ollama_functions/)
- [MyScript Developer Portal](https://developer.myscript.com/)
- Project GitHub Repository
