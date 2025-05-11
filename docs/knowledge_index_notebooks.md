# Knowledge Index Notebooks

InkLink provides a powerful feature that generates navigable index notebooks for knowledge organization. These index notebooks are automatically generated in EPUB format with hyperlinks, making them easy to navigate on your reMarkable tablet.

## Overview

Knowledge index notebooks organize your content into structured, browsable references. Each index notebook provides a different way to explore your knowledge:

1. **Entity Index**: Organizes entities by type with references to where they appear
2. **Topic Index**: Shows important topics with their connections and relationships
3. **Notebook Index**: Lists notebooks and their pages with key entities
4. **Master Index**: Combines all index types into one comprehensive reference

## EPUB Format with Hyperlinks

All index notebooks are generated in EPUB format, which offers several advantages:

- **Hyperlinked Navigation**: Jump directly between connected entities and topics
- **Structured Table of Contents**: Easily navigate through sections
- **Consistent Formatting**: Clean, readable presentation on reMarkable

The EPUB format preserves the readability of content while adding interactive features that make browsing your knowledge more efficient.

## Index Types

### Entity Index

The entity index organizes entities by type (Person, Concept, Technology, etc.) and provides:

- Brief descriptions and observations
- References to notebooks and pages where the entity appears
- Lists of related entities with relationship types

Example entity entry:
```
### Machine Learning

**Description:**
- A field of study that gives computers the ability to learn without being explicitly programmed.
- Often uses statistical techniques to give computers the ability to improve with experience.

**References:**
- AI Research, page 3: ML Fundamentals
- AI Research, page 15: Neural Networks

**Related Entities:**
- includes Neural Networks
- related to Data Science
- is a subset of Artificial Intelligence
```

### Topic Index

The topic index focuses on important topics based on their connections within the knowledge graph:

- Organized by importance (number of connections)
- Shows related entities grouped by relationship type
- Provides references to source material

Example topic entry:
```
## Machine Learning

**Type:** Concept
**Connections:** 15

**Description:**
- A field of study that gives computers the ability to learn without being explicitly programmed.
- Often uses statistical techniques to give computers the ability to improve with experience.

**Related Entities:**

*INCLUDES:*
- Neural Networks
- Deep Learning
- Reinforcement Learning

*USED_FOR:*
- Image Recognition
- Natural Language Processing

**References:**
- AI Research, page 3: ML Fundamentals
- AI Research, page 15: Neural Networks
```

### Notebook Index

The notebook index organizes content by its source notebooks:

- Lists all notebooks with their pages
- Shows page titles and key entities mentioned
- Presented in a tabular format for easy scanning

Example notebook section:
```
## AI Research

| Page | Title | Key Entities |
|------|-------|-------------|
| 1 | AI Introduction | Artificial Intelligence, Computer Science, Turing Test |
| 3 | ML Fundamentals | Machine Learning, Supervised Learning, Unsupervised Learning |
| 8 | Implementation | Python, Machine Learning, Libraries |
| 15 | Neural Networks | Neural Networks, Machine Learning, Deep Learning |
```

### Master Index

The master index combines all three index types into a single comprehensive reference:

- Includes entity, topic, and notebook sections
- Adds cross-references between related items
- Provides a unified table of contents

## Creating Index Notebooks

Index notebooks can be generated through the API or using the InkLink CLI.

### API

```python
# Create an entity index
POST /api/knowledge/indexes/entity
{
  "entity_types": ["Person", "Concept"],  # Optional
  "min_references": 1,                   # Optional
  "upload_to_remarkable": true           # Optional
}

# Create a topic index
POST /api/knowledge/indexes/topic
{
  "top_n_topics": 20,                    # Optional
  "min_connections": 2,                  # Optional
  "upload_to_remarkable": true           # Optional
}

# Create a notebook index
POST /api/knowledge/indexes/notebook
{
  "upload_to_remarkable": true           # Optional
}

# Create a master index
POST /api/knowledge/indexes/master
{
  "upload_to_remarkable": true           # Optional
}
```

### CLI

```bash
# Create an entity index
inklink knowledge index create-entity --types Person,Concept --min-references 1

# Create a topic index
inklink knowledge index create-topic --top-n 20 --min-connections 2

# Create a notebook index
inklink knowledge index create-notebook

# Create a master index
inklink knowledge index create-master
```

## Technical Implementation

The index notebook feature is implemented through the following components:

1. **EPUBGenerator**: Creates EPUB documents with hyperlinks from markdown content
2. **KnowledgeIndexService**: Generates different types of index notebooks
3. **DocumentService**: Converts content to reMarkable format as a fallback
4. **RemarkableService**: Uploads generated indexes to reMarkable Cloud

### Hyperlink Generation

The system automatically enhances the index content with hyperlinks by:

1. Creating a map of entity/topic names to anchor IDs
2. Processing markdown content to add hyperlinks to entity names
3. Preserving the hyperlinks during EPUB generation

The hyperlinks are carefully inserted only in appropriate contexts, avoiding links in headings or existing links.

## Fallback Mechanism

While index notebooks are always generated in EPUB format, the system also creates a reMarkable format (.rm) version as a fallback. This ensures compatibility even if there are issues with the EPUB generation.

## Future Enhancements

Planned enhancements for index notebooks include:

1. Automatic index updates when new content is added
2. Custom index templates for different knowledge domains
3. Personal annotation preservation across index updates
4. Integration with external knowledge sources
5. Custom styling options for EPUB presentation