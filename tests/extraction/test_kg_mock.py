"""Mock implementation of KnowledgeGraphService for testing."""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

from inklink.services.interfaces import IKnowledgeGraphService

logger = logging.getLogger(__name__)


class MockKnowledgeGraphService(IKnowledgeGraphService):
    """Mock implementation of KnowledgeGraphService for testing."""

    def __init__(self, *args, **kwargs):
        """Initialize the mock knowledge graph service."""
        self.entities = {}
        self.relationships = []

    def extract_entities(self, content: str) -> List[Dict[str, Any]]:
        """Mock entity extraction."""
        logger.info(f"Extracting entities from content ({len(content)} chars)")
        return [
            {"id": "entity1", "name": "Entity 1", "type": "Concept"},
            {"id": "entity2", "name": "Entity 2", "type": "Person"},
        ]

    def extract_relationships(self, content: str) -> List[Dict[str, Any]]:
        """Mock relationship extraction."""
        logger.info(f"Extracting relationships from content ({len(content)} chars)")
        return [
            {
                "from_id": "entity1",
                "to_id": "entity2",
                "type": "MENTIONS",
                "source": "test",
            }
        ]

    def add_entity(self, entity: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Mock entity addition."""
        entity_id = entity.get("id", f"e-{len(self.entities)}")
        self.entities[entity_id] = entity
        return True, {"id": entity_id, "name": entity.get("name", "Unknown")}

    def add_relationship(
        self, relationship: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Mock relationship addition."""
        self.relationships.append(relationship)
        return True, {
            "id": f"r-{len(self.relationships)}",
            "type": relationship.get("type", "Unknown"),
        }

    def delete_entities_by_source(self, source: str) -> Tuple[bool, Dict[str, Any]]:
        """Mock entity deletion by source."""
        deleted = []
        for entity_id, entity in list(self.entities.items()):
            if entity.get("source") == source:
                deleted.append(entity_id)
                del self.entities[entity_id]

        return True, {"deleted_count": len(deleted), "deleted_ids": deleted}

    # Required methods from IKnowledgeGraphService
    def get_entities(
        self, types: Optional[List[str]] = None, min_references: int = 0
    ) -> List[Dict[str, Any]]:
        """Get entities from the knowledge graph."""
        result = []
        for entity_id, entity in self.entities.items():
            if types and entity.get("type") not in types:
                continue

            # Simulate references
            references = []
            observations = entity.get("metadata", {}).get("observations", [])
            if observations:
                for obs in observations:
                    references.append(
                        {"notebook": "Test Notebook", "page": "1", "context": obs[:100]}
                    )

            if len(references) >= min_references:
                result.append(
                    {
                        "name": entity.get("name", "Unknown"),
                        "type": entity.get("type", "Unknown"),
                        "references": references,
                    }
                )

        return result

    def get_topics(
        self, limit: int = 20, min_connections: int = 2
    ) -> List[Dict[str, Any]]:
        """Get topics from the knowledge graph."""
        # Just return a mock topic
        return [
            {
                "name": "Test Topic",
                "description": "Test topic for testing",
                "connections": [
                    {"entity": "Entity 1", "entity_type": "Concept", "strength": 0.8},
                    {"entity": "Entity 2", "entity_type": "Person", "strength": 0.7},
                ],
            }
        ]

    def get_notebooks(self) -> List[Dict[str, Any]]:
        """Get notebooks from the knowledge graph."""
        return [
            {
                "name": "Test Notebook",
                "entities": [
                    {"name": "Entity 1", "type": "Concept", "count": 2},
                    {"name": "Entity 2", "type": "Person", "count": 1},
                ],
                "topics": [{"name": "Test Topic", "relevance": 0.8}],
            }
        ]
