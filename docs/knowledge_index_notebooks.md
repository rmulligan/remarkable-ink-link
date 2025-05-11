# Knowledge Index Notebooks

This document describes the Knowledge Index Notebooks feature of InkLink, which creates structured EPUB indexes for organizing content on reMarkable tablets.

## Overview

Knowledge Index Notebooks provide a convenient way to navigate and reference content across your reMarkable notebook collection. The feature uses InkLink's knowledge graph to generate hyperlinked EPUB documents that organize entities, topics, and notebooks for easy exploration.

### Key Features

- **EPUB Format with Hyperlinks**: All index notebooks are generated in EPUB format with clickable links for navigation between related content
- **Multiple Index Types**: Create specialized indexes focused on entities, topics, notebooks, or a comprehensive master index
- **Direct reMarkable Integration**: Index notebooks can be automatically uploaded to reMarkable Cloud
- **Semantic Organization**: Content is organized based on meaning and relationships, not just keywords

### Index Types

1. **Entity Index**: Groups entities by type (people, places, concepts, etc.) with references to source notebooks and pages
2. **Topic Index**: Organizes content by topic, showing the most relevant entities and connections for each topic
3. **Notebook Index**: Lists all notebooks with their key entities, topics, and page references
4. **Master Index**: A comprehensive index combining all of the above for complete knowledge navigation

## Usage

### Command Line Interface

The most direct way to create knowledge index notebooks is through the CLI:

```bash
# Create an entity index and upload to reMarkable
python -m inklink.main create-entity-index

# Create a topic index with custom parameters
python -m inklink.main create-topic-index --top-n 30 --min-connections 3

# Create a notebook index
python -m inklink.main create-notebook-index

# Create a comprehensive master index 
python -m inklink.main create-master-index
```

### API Usage

You can also create index notebooks programmatically:

```python
from inklink.di.container import Container
from inklink.services.knowledge_index_service import KnowledgeIndexService

# Get service via dependency injection
config = {}  # Configuration can be customized if needed
provider = Container.create_provider(config)
index_service = provider.get(KnowledgeIndexService)

# Create an entity index
success, result = index_service.create_entity_index(
    entity_types=["Person", "Concept", "Project"], 
    min_references=2,
    upload_to_remarkable=True
)

# Create a topic index
success, result = index_service.create_topic_index(
    top_n_topics=20,
    min_connections=2,
    upload_to_remarkable=True
)

# Create a notebook index
success, result = index_service.create_notebook_index(
    upload_to_remarkable=True
)

# Create a master index
success, result = index_service.create_master_index(
    upload_to_remarkable=True
)
```

### MCP Integration

Knowledge Index Notebooks are available as Model Context Protocol (MCP) tools, enabling Claude and other MCP-compatible interfaces to create and manage index notebooks:

```python
# Example MCP request to create an entity index
response = mcp.call_tool("create_entity_index", {
    "entity_types": ["Person", "Concept"],
    "min_references": 2,
    "upload_to_remarkable": True
})

# Example MCP request to create a master index
response = mcp.call_tool("create_master_index", {
    "upload_to_remarkable": True
})
```

## Technical Implementation

### Architecture

The EPUB Index Notebooks feature is composed of several components:

1. **KnowledgeIndexService**: Core service that generates different types of index notebooks
2. **EPUBGenerator**: Service for creating EPUB documents with hyperlinks
3. **KnowledgeGraphService**: Interface to the Neo4j knowledge graph for retrieving entities, topics, and notebooks
4. **RemarkableAdapter**: Adapter for uploading generated EPUB files to reMarkable Cloud

### EPUB Format

All index notebooks are inherently generated in EPUB format (not configurable) to provide the best navigation experience on reMarkable tablets. Each EPUB document includes:

- **Structured Hierarchy**: Content organized in clear sections with headings
- **Hyperlinks**: Clickable links between related content
- **Optimized Typography**: Styling optimized for reMarkable display
- **Anchors**: Named anchors for direct navigation to specific entities or topics

### Dependency Injection

The feature integrates with InkLink's dependency injection system:

```python
# in src/inklink/di/container.py
from inklink.services.knowledge_index_service import KnowledgeIndexService
from inklink.services.epub_generator import EPUBGenerator

# ...

def create_provider(config):
    # ...
    
    # Register EPUB generator service
    provider.register(
        EPUBGenerator,
        lambda: EPUBGenerator(output_dir=config.get("OUTPUT_DIR"))
    )
    
    # Register knowledge index service
    provider.register(
        KnowledgeIndexService,
        lambda: KnowledgeIndexService(
            knowledge_graph_service=provider.get(KnowledgeGraphService),
            epub_generator=provider.get(EPUBGenerator),
            remarkable_adapter=provider.get(RemarkableAdapter),
            output_dir=config.get("OUTPUT_DIR")
        )
    )
```

## Example Use Cases

### Research Organization

Researchers can use Knowledge Index Notebooks to:

1. Create an Entity Index of key concepts, people, and papers mentioned in their notes
2. Generate a Topic Index to see how different research areas connect
3. Use the Master Index to navigate between related ideas and source materials

### Project Management

Project managers can use Knowledge Index Notebooks to:

1. Track team members and stakeholders via the Entity Index
2. Monitor project topics and themes via the Topic Index
3. Navigate project notebooks via the Notebook Index
4. Create a Master Index for comprehensive project navigation

### Learning and Education

Students can use Knowledge Index Notebooks to:

1. Create an Entity Index of key concepts and definitions
2. Generate a Topic Index to see the relationships between different subjects
3. Use the Notebook Index to organize course notes
4. Create a Master Index for exam preparation

## Future Enhancements

Planned enhancements for Knowledge Index Notebooks include:

1. **Visual Indicators**: Add visual cues for entity types and relationship strengths
2. **Customizable Templates**: Allow users to customize the appearance and structure of index notebooks
3. **Incremental Updates**: Support for updating existing index notebooks without regenerating from scratch
4. **Advanced Filtering**: More sophisticated filtering options for entities and topics
5. **Bi-directional Linking**: Create backlinks from source notebooks to index notebooks

## Technical Reference

### KnowledgeIndexService Methods

```python
def create_entity_index(
    self,
    entity_types: Optional[List[str]] = None,
    min_references: int = 1,
    upload_to_remarkable: bool = True,
) -> Tuple[bool, Dict[str, Any]]

def create_topic_index(
    self,
    top_n_topics: int = 20,
    min_connections: int = 2,
    upload_to_remarkable: bool = True,
) -> Tuple[bool, Dict[str, Any]]

def create_notebook_index(
    self,
    upload_to_remarkable: bool = True,
) -> Tuple[bool, Dict[str, Any]]

def create_master_index(
    self,
    upload_to_remarkable: bool = True,
) -> Tuple[bool, Dict[str, Any]]
```

### EPUBGenerator Methods

```python
def create_epub_from_markdown(
    self, 
    title: str, 
    content: str, 
    author: str = "InkLink",
    entity_links: Dict[str, str] = None,
    metadata: Dict[str, Any] = None
) -> Tuple[bool, Dict[str, Any]]

def enhance_markdown_with_hyperlinks(
    self, 
    markdown_content: str, 
    entity_links: Dict[str, str]
) -> str
```

## Troubleshooting

### Common Issues

1. **Missing Content**: If entities or topics aren't appearing in the index, they may not meet the minimum reference or connection requirements. Try lowering the thresholds.

2. **Upload Failures**: If the index isn't uploading to reMarkable, check that rmapi is properly configured and authenticated. Also verify that the reMarkable adapter is correctly initialized.

3. **Slow Generation**: For large knowledge graphs, index generation can be time-consuming. Consider using more specific entity types or increasing minimum thresholds to reduce the amount of content included.

4. **Broken Links**: If links in the EPUB aren't working, ensure that the entity names and anchor IDs are correctly formatted. Special characters in entity names can sometimes cause issues.

### Logging

Enable DEBUG level logging to get more information about the index generation process:

```python
import logging
logging.getLogger('inklink.services.knowledge_index_service').setLevel(logging.DEBUG)
logging.getLogger('inklink.services.epub_generator').setLevel(logging.DEBUG)
```

## Conclusion

Knowledge Index Notebooks provide a powerful way to organize and navigate your reMarkable content through semantically linked EPUB documents. By generating different types of indexes, you can explore your notes from multiple perspectives, finding connections and insights that might otherwise be missed.