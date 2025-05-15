# EPUB Index Notebooks for Knowledge Organization

## Overview

This PR implements a comprehensive system for creating and managing knowledge index notebooks in EPUB format with hyperlinks. These notebooks provide an organized way to navigate through entities, topics, and notebooks in the reMarkable ecosystem.

## Key Features

- **EPUB Generator Service**: Creates EPUB documents with hyperlinks for navigation
- **Knowledge Graph Service**: Provides interface to Neo4j for entity and relationship management
- **Knowledge Index Service**: Creates four types of index notebooks:
  - Entity Index: Organizes entities by type with references
  - Topic Index: Organizes content by topic with connections
  - Notebook Index: Lists notebooks with their content and entities
  - Master Index: Combines all indexes for comprehensive navigation

## Technical Details

- EPUB format is inherent (not configurable) for all index notebooks
- Uses Neo4j for graph database storage and queries
- Integrates with reMarkable Cloud via rmapi adapter
- CLI commands for creating different index types
- Comprehensive error handling and logging
- Full test coverage

## Implementation Details

- Added new services:
  - : For creating EPUB documents with hyperlinks
  - : Interface to Neo4j database
  - : Business logic for index creation
- Updated container.py for dependency injection
- Added interfaces for new services
- Included tests for all new functionality
- Documented the feature in knowledge_index_notebooks.md

## Dependencies

- Added new dependencies:
  - ebooklib: For EPUB file generation
  - neo4j: For knowledge graph database
  - sentence-transformers: For semantic linking

## Testing

- Unit tests for EPUBGenerator
- Unit tests for KnowledgeIndexService
- Tested actual EPUB generation and upload to reMarkable
- Validated all integration points

## Documentation

- Added comprehensive documentation in docs/knowledge_index_notebooks.md
- Included CLI examples and API usage
- Provided detailed description of index types and their organization

## Future Enhancements

1. Visual indicators for entity types and relationship strengths
2. Customizable templates for index appearance
3. Incremental updates to existing index notebooks
4. More sophisticated filtering options
