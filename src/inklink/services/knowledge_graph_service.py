"""Service for interacting with the knowledge graph."""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from inklink.config import CONFIG
from inklink.services.ai_service import AIService
from inklink.services.interfaces import IKnowledgeGraphService

logger = logging.getLogger(__name__)


class KnowledgeGraphService(IKnowledgeGraphService):
    """
    Service for creating, managing, and querying knowledge graph data.

    This service provides a unified interface for knowledge graph operations,
    including entity extraction, relationship extraction, semantic search,
    and knowledge graph management.
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ai_service: Optional[AIService] = None,
    ):
        """
        Initialize the knowledge graph service.

        Args:
            uri: Neo4j URI (defaults to environment variable)
            username: Neo4j username (defaults to environment variable)
            password: Neo4j password (defaults to environment variable)
            ai_service: Service for AI processing (optional)
        """
        # Set Neo4j connection parameters
        self.uri = uri or CONFIG.get("NEO4J_URI", "bolt://localhost:7687")
        self.username = username or CONFIG.get("NEO4J_USERNAME", "neo4j")
        self.password = password or CONFIG.get("NEO4J_PASSWORD", "password")

        # Set up AI service for extraction and embedding tasks
        self.ai_service = ai_service or AIService()

        # Initialize connection on first access
        self._driver = None

    def get_driver(self):
        """Get or create Neo4j driver."""
        if self._driver is None:
            try:
                # Import here to avoid dependency if Neo4j is not used
                from neo4j import GraphDatabase

                self._driver = GraphDatabase.driver(
                    self.uri, auth=(self.username, self.password)
                )
                logger.info(f"Connected to Neo4j at {self.uri}")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j database: {e}")
                self._driver = None

        return self._driver

    def is_connected(self) -> bool:
        """
        Check if the connection to Neo4j is working.

        Returns:
            True if connection is working, False otherwise
        """
        try:
            driver = self.get_driver()
            if driver:
                with driver.session() as session:
                    result = session.run("RETURN 1 as test")
                    return result.single()["test"] == 1
            return False
        except Exception as e:
            logger.error(f"Error checking Neo4j connection: {e}")
            return False

    def extract_entities_from_text(
        self, text: str, entity_types: Optional[List[str]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Extract entities from text using AI analysis.

        Args:
            text: The text to extract entities from
            entity_types: Optional list of entity types to extract

        Returns:
            Tuple of (success, result dictionary)
        """
        try:
            logger.info("Extracting entities from text")

            # Create a prompt to extract entities using AI service
            type_filter = ""
            if entity_types:
                type_filter = f"Only extract entities of the following types: {', '.join(entity_types)}."

            prompt = f"""
            Extract key entities/concepts from the following text:

            {text}

            {type_filter}

            For each entity, provide:
            1. The entity name
            2. The entity type (e.g., Person, Organization, Concept, Technology, etc.)
            3. A confidence score from 0.0 to 1.0
            4. The context (the sentence or phrase where it appears)

            Return the results as a JSON array with objects containing "name", "type", "score", and "context" fields.
            Only include entities with a confidence score of 0.5 or higher.
            """

            response = self.ai_service.generate_text(prompt, max_tokens=1500)

            # Parse the response
            try:
                # Clean the response to ensure it's valid JSON
                # Find JSON array starting with [ and ending with ]
                import re

                json_match = re.search(r"\[.*\]", response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    entities = json.loads(json_str)
                else:
                    # Try to parse the whole response as JSON
                    entities = json.loads(response)
                    if not isinstance(entities, list):
                        if isinstance(entities, dict) and "entities" in entities:
                            entities = entities["entities"]
                        else:
                            return False, {
                                "error": "Invalid response format, expected a list of entities"
                            }

                return True, {"count": len(entities), "entities": entities}
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Failed to parse entity extraction response as JSON: {e}"
                )
                # As a fallback, try to extract entities with simple heuristics
                entities = self._extract_entities_heuristic(text)
                return True, {"count": len(entities), "entities": entities}

        except Exception as e:
            logger.error(f"Error extracting entities from text: {e}")
            return False, {"error": f"Entity extraction failed: {str(e)}"}

    @staticmethod
    def _extract_entities_heuristic(text: str) -> List[Dict[str, Any]]:
        """
        Simple heuristic-based entity extraction as fallback.

        Args:
            text: Text to extract entities from

        Returns:
            List of extracted entities
        """
        entities = []

        # Split text into sentences
        sentences = text.split(".")

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Extract nouns that start with capitals as potential entities
            words = sentence.split()
            for word in words:
                word = word.strip()
                if len(word) > 1 and word[0].isupper():
                    # Remove punctuation
                    clean_word = "".join(c for c in word if c.isalnum() or c.isspace())
                    if clean_word:
                        entities.append(
                            {
                                "name": clean_word,
                                "type": "Concept",
                                "score": 0.6,
                                "context": sentence,
                            }
                        )

        # Remove duplicates
        unique_entities = []
        seen_names = set()
        for entity in entities:
            if entity["name"] not in seen_names:
                seen_names.add(entity["name"])
                unique_entities.append(entity)

        return unique_entities

    def extract_relationships_from_text(
        self, text: str, from_entity: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Extract relationships from text using AI analysis.

        Args:
            text: The text to extract relationships from
            from_entity: Optional entity to focus on as the source of relationships

        Returns:
            Tuple of (success, result dictionary)
        """
        try:
            logger.info("Extracting relationships from text")

            # Create a prompt to extract relationships using AI service
            entity_filter = ""
            if from_entity:
                entity_filter = f"Only extract relationships where '{from_entity}' is the source entity."

            prompt = f"""
            Extract semantic relationships between entities/concepts from the following text:

            {text}

            {entity_filter}

            For each relationship, provide:
            1. The source entity (from)
            2. The target entity (to)
            3. The relationship type (e.g., PART_OF, WORKS_FOR, INSTANCE_OF, etc.)
            4. A confidence score from 0.0 to 1.0

            Return the results as a JSON array with objects containing "from", "to", "type", and "score" fields.
            Only include relationships with a confidence score of 0.5 or higher.
            """

            response = self.ai_service.generate_text(prompt, max_tokens=1500)

            # Parse the response
            try:
                # Clean the response to ensure it's valid JSON
                import re

                json_match = re.search(r"\[.*\]", response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    relationships = json.loads(json_str)
                else:
                    # Try to parse the whole response as JSON
                    relationships = json.loads(response)
                    if not isinstance(relationships, list):
                        if (
                            isinstance(relationships, dict)
                            and "relationships" in relationships
                        ):
                            relationships = relationships["relationships"]
                        else:
                            return False, {
                                "error": "Invalid response format, expected a list of relationships"
                            }

                # Filter relationships if from_entity is specified
                if from_entity:
                    relationships = [
                        r for r in relationships if r.get("from") == from_entity
                    ]

                return True, {
                    "count": len(relationships),
                    "relationships": relationships,
                }
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Failed to parse relationship extraction response as JSON: {e}"
                )
                # As a fallback, return an empty list
                return True, {"count": 0, "relationships": []}

        except Exception as e:
            logger.error(f"Error extracting relationships from text: {e}")
            return False, {"error": f"Relationship extraction failed: {str(e)}"}

    def create_entity(
        self, name: str, entity_type: str, observations: Optional[List[str]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a new entity in the knowledge graph.

        Args:
            name: Entity name (must be unique)
            entity_type: Type of entity
            observations: List of text observations about the entity

        Returns:
            Tuple of (success, entity information)
        """
        try:
            logger.info(f"Creating entity: {name} ({entity_type})")

            driver = self.get_driver()
            if not driver:
                return False, {"error": "Neo4j connection not available"}

            # Prepare observations
            observations = observations or []
            properties = {"observations": observations}

            # Create entity
            with driver.session() as session:
                result = session.run(
                    """
                    MERGE (e:Entity {name: $name})
                    SET e.type = $type,
                        e.properties = $properties,
                        e.created = TIMESTAMP(),
                        e.updated = TIMESTAMP()
                    RETURN e
                    """,
                    name=name,
                    type=entity_type,
                    properties=properties,
                )

                record = result.single()
                if not record:
                    return False, {"error": "Failed to create entity"}

                entity = record["e"]
                return True, {
                    "id": entity.id,
                    "name": entity.get("name"),
                    "type": entity.get("type"),
                    "properties": entity.get("properties", {}),
                }

        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            return False, {"error": f"Entity creation failed: {str(e)}"}

    def get_entity(self, name: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get an entity from the knowledge graph.

        Args:
            name: Entity name

        Returns:
            Tuple of (success, entity information)
        """
        try:
            logger.info(f"Getting entity: {name}")

            driver = self.get_driver()
            if not driver:
                return False, {"error": "Neo4j connection not available"}

            # Get entity
            with driver.session() as session:
                result = session.run(
                    """
                    MATCH (e:Entity {name: $name})
                    RETURN e
                    """,
                    name=name,
                )

                record = result.single()
                if not record:
                    return False, {"error": "Entity not found"}

                entity = record["e"]
                return True, {
                    "id": entity.id,
                    "name": entity.get("name"),
                    "type": entity.get("type"),
                    "properties": entity.get("properties", {}),
                }

        except Exception as e:
            logger.error(f"Error getting entity: {e}")
            return False, {"error": f"Entity retrieval failed: {str(e)}"}

    def create_relationship(
        self, from_entity: str, to_entity: str, relationship_type: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a relationship between entities.

        Args:
            from_entity: Source entity name
            to_entity: Target entity name
            relationship_type: Type of relationship

        Returns:
            Tuple of (success, relationship information)
        """
        try:
            logger.info(
                f"Creating relationship: {from_entity} -{relationship_type}-> {to_entity}"
            )

            driver = self.get_driver()
            if not driver:
                return False, {"error": "Neo4j connection not available"}

            # Create relationship
            with driver.session() as session:
                result = session.run(
                    f"""
                    MATCH (a:Entity {{name: $from_entity}})
                    MATCH (b:Entity {{name: $to_entity}})
                    MERGE (a)-[r:{relationship_type}]->(b)
                    SET r.created = TIMESTAMP()
                    RETURN r, a.name as from_name, b.name as to_name, TYPE(r) as type
                    """,
                    from_entity=from_entity,
                    to_entity=to_entity,
                )

                record = result.single()
                if not record:
                    return False, {"error": "Failed to create relationship"}

                rel = record["r"]
                return True, {
                    "id": rel.id,
                    "from": record["from_name"],
                    "to": record["to_name"],
                    "type": record["type"],
                }

        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return False, {"error": f"Relationship creation failed: {str(e)}"}

    def get_entity_relationships(self, entity_name: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get relationships for an entity.

        Args:
            entity_name: Entity name

        Returns:
            Tuple of (success, relationship information)
        """
        try:
            logger.info(f"Getting relationships for entity: {entity_name}")

            driver = self.get_driver()
            if not driver:
                return False, {"error": "Neo4j connection not available"}

            # Get relationships
            with driver.session() as session:
                result = session.run(
                    """
                    MATCH (e:Entity {name: $name})-[r]->(target:Entity)
                    RETURN target.name as target_name, target.type as target_type, TYPE(r) as relationship_type
                    UNION
                    MATCH (source:Entity)-[r]->(e:Entity {name: $name})
                    RETURN source.name as source_name, source.type as source_type, TYPE(r) as relationship_type
                    """,
                    name=entity_name,
                )

                related_entities = []
                for record in result:
                    if "target_name" in record:
                        related_entities.append(
                            {
                                "entity": record["target_name"],
                                "type": record["target_type"],
                                "relationship": record["relationship_type"],
                                "direction": "outgoing",
                            }
                        )
                    else:
                        related_entities.append(
                            {
                                "entity": record["source_name"],
                                "type": record["source_type"],
                                "relationship": record["relationship_type"],
                                "direction": "incoming",
                            }
                        )

                return True, {
                    "entity": entity_name,
                    "related_entities": related_entities,
                }

        except Exception as e:
            logger.error(f"Error getting entity relationships: {e}")
            return False, {"error": f"Relationship retrieval failed: {str(e)}"}

    def create_semantic_links(
        self,
        entity_name: str,
        min_similarity: float = 0.7,
        max_links: int = 5,
        entity_types: Optional[List[str]] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create semantic links for an entity.

        Args:
            entity_name: Entity name
            min_similarity: Minimum similarity score (0-1)
            max_links: Maximum number of links to create
            entity_types: Optional list of entity types to link with

        Returns:
            Tuple of (success, result information)
        """
        try:
            logger.info(f"Creating semantic links for entity: {entity_name}")

            # Get entity first
            success, entity_result = self.get_entity(entity_name)
            if not success:
                return False, {"error": f"Entity not found: {entity_name}"}

            # Get entity text for embedding
            entity = entity_result
            entity_text = entity_name
            if "properties" in entity and "observations" in entity["properties"]:
                entity_text += ". " + ". ".join(entity["properties"]["observations"])

            # Find similar entities using semantic search
            success, search_result = self.find_semantically_similar_text(
                text=entity_text,
                min_similarity=min_similarity,
                max_results=max_links,
                entity_types=entity_types,
                exclude_entities=[entity_name],
            )

            if not success:
                return False, {
                    "error": f"Semantic search failed: {search_result.get('error')}"
                }

            similar_entities = search_result.get("results", [])

            # Create semantic links
            links_created = 0
            for similar in similar_entities:
                similar_entity = similar.get("entity")
                # Create SEMANTICALLY_SIMILAR_TO relationship
                success, _ = self.create_relationship(
                    from_entity=entity_name,
                    to_entity=similar_entity,
                    relationship_type="SEMANTICALLY_SIMILAR_TO",
                )

                if success:
                    links_created += 1

            return True, {
                "entity": entity_name,
                "similar_entities": similar_entities,
                "links_created": links_created,
            }

        except Exception as e:
            logger.error(f"Error creating semantic links: {e}")
            return False, {"error": f"Semantic link creation failed: {str(e)}"}

    def find_semantically_similar_text(
        self,
        text: str,
        min_similarity: float = 0.6,
        max_results: int = 10,
        entity_types: Optional[List[str]] = None,
        exclude_entities: Optional[List[str]] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Find semantically similar entities to the given text.

        Args:
            text: Query text
            min_similarity: Minimum similarity score (0-1)
            max_results: Maximum number of results
            entity_types: Optional list of entity types to filter by
            exclude_entities: Optional list of entity names to exclude

        Returns:
            Tuple of (success, result information)
        """
        try:
            logger.info(f"Finding semantically similar text: {text[:50]}...")

            # Embed query text and find similar entities
            # (Since we're mocking this, we'll create a simulated response)
            # In a real implementation, we would use vector embeddings and similarity search

            # Use AI service to generate a list of related concepts
            type_filter = ""
            if entity_types:
                type_filter = f"Only include entities of the following types: {', '.join(entity_types)}."

            exclude_filter = ""
            if exclude_entities:
                exclude_filter = f"Do not include any of these entities: {', '.join(exclude_entities)}."

            prompt = f"""
            Find concepts, ideas, or entities that are semantically similar to this text:

            {text}

            {type_filter}
            {exclude_filter}

            For each similar concept, provide:
            1. The entity name
            2. The entity type (e.g., Person, Organization, Concept, Technology, etc.)
            3. A similarity score from 0.0 to 1.0 (where 1.0 is identical)

            Return the results as a JSON array with objects containing "entity", "type", and "similarity" fields.
            Only include entities with a similarity score of {min_similarity} or higher.
            Sort results by similarity score in descending order.
            Limit results to {max_results} items.
            """

            response = self.ai_service.generate_text(prompt, max_tokens=1500)

            # Parse the response
            try:
                # Clean the response to ensure it's valid JSON
                import re

                json_match = re.search(r"\[.*\]", response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    similar_entities = json.loads(json_str)
                else:
                    # Try to parse the whole response as JSON
                    similar_entities = json.loads(response)
                    if not isinstance(similar_entities, list):
                        if (
                            isinstance(similar_entities, dict)
                            and "results" in similar_entities
                        ):
                            similar_entities = similar_entities["results"]
                        else:
                            return False, {
                                "error": "Invalid response format, expected a list of similar entities"
                            }

                # Sort by similarity and limit results
                similar_entities = sorted(
                    similar_entities, key=lambda x: x.get("similarity", 0), reverse=True
                )
                similar_entities = similar_entities[:max_results]

                return True, {
                    "query": text,
                    "results": similar_entities,
                    "count": len(similar_entities),
                }
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse semantic search response as JSON: {e}")
                # As a fallback, return an empty list
                return True, {"query": text, "results": [], "count": 0}

        except Exception as e:
            logger.error(f"Error finding semantically similar text: {e}")
            return False, {"error": f"Semantic search failed: {str(e)}"}

    # Required methods for IKnowledgeGraphService interface
    def get_entities(
        self, types: Optional[List[str]] = None, min_references: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get entities from the knowledge graph, optionally filtered by type.

        Args:
            types: Optional list of entity types to filter by
            min_references: Minimum number of references for an entity to be included

        Returns:
            List of entity dictionaries
        """
        try:
            logger.info("Getting entities from knowledge graph")
            driver = self.get_driver()
            if not driver:
                logger.error("Neo4j connection not available")
                return []

            entities = []
            # Get all entities from graph
            with driver.session() as session:
                query = "MATCH (e:Entity)"
                if types:
                    type_list = ", ".join([f"'{t}'" for t in types])
                    query += f" WHERE e.type IN [{type_list}]"
                query += " RETURN e"

                result = session.run(query)

                for record in result:
                    entity = record["e"]
                    entity_data = {
                        "name": entity.get("name"),
                        "type": entity.get("type"),
                        "references": [],  # Default empty references
                    }

                    # Get metadata and properties
                    properties = entity.get("properties", {})
                    if (
                        properties
                        and isinstance(properties, dict)
                        and "observations" in properties
                    ):
                        for obs in properties["observations"]:
                            if isinstance(obs, str) and len(obs) > 0:
                                # Create a reference from the observation
                                entity_data["references"].append(
                                    {
                                        "notebook": "Unknown",
                                        "page": "0",
                                        "context": obs[
                                            :100
                                        ],  # Truncate long observations
                                    }
                                )

                    if len(entity_data["references"]) >= min_references:
                        entities.append(entity_data)

            return entities

        except Exception as e:
            logger.error(f"Error getting entities: {e}")
            return []

    def get_topics(
        self, limit: int = 20, min_connections: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get topics from the knowledge graph.

        Topics are derived from entity clusters and semantic connections.

        Args:
            limit: Maximum number of topics to return
            min_connections: Minimum number of connections for a topic to be included

        Returns:
            List of topic dictionaries
        """
        try:
            logger.info("Getting topics from knowledge graph")

            # For now, simulate topics by clustering entities by type
            topics = []
            entities = self.get_entities()

            # Group entities by type
            type_groups = {}
            for entity in entities:
                entity_type = entity.get("type", "Unknown")
                if entity_type not in type_groups:
                    type_groups[entity_type] = []
                type_groups[entity_type].append(entity)

            # Create a topic for each entity type with enough connections
            for entity_type, entity_list in type_groups.items():
                if len(entity_list) >= min_connections:
                    connections = []
                    for entity in entity_list:
                        connections.append(
                            {
                                "entity": entity["name"],
                                "entity_type": entity["type"],
                                "strength": 0.8,  # Default strength
                            }
                        )

                    topics.append(
                        {
                            "name": f"{entity_type} Concepts",
                            "description": f"Collection of {entity_type} concepts",
                            "connections": connections,
                        }
                    )

            # Sort topics by number of connections and limit results
            topics.sort(key=lambda x: len(x["connections"]), reverse=True)
            return topics[:limit]

        except Exception as e:
            logger.error(f"Error getting topics: {e}")
            return []

    def get_notebooks(self) -> List[Dict[str, Any]]:
        """
        Get notebooks from the knowledge graph.

        Returns:
            List of notebook dictionaries with their entities and topics
        """
        try:
            logger.info("Getting notebooks from knowledge graph")

            # For now, simulate notebooks by collecting unique references
            notebooks = {}
            entities = self.get_entities()

            # Collect notebook references from entities
            for entity in entities:
                for reference in entity.get("references", []):
                    notebook_name = reference.get("notebook", "Unknown")
                    if notebook_name == "Unknown":
                        continue

                    if notebook_name not in notebooks:
                        notebooks[notebook_name] = {
                            "name": notebook_name,
                            "entities": [],
                            "topics": [],
                        }

                    # Add entity to notebook if not already present
                    entity_entry = {
                        "name": entity["name"],
                        "type": entity["type"],
                        "count": 1,
                    }

                    if entity_entry not in notebooks[notebook_name]["entities"]:
                        notebooks[notebook_name]["entities"].append(entity_entry)

            # Get topics and link them to notebooks
            topics = self.get_topics()
            for notebook_name, notebook in notebooks.items():
                for topic in topics:
                    # Check if any topic entities are in the notebook
                    for connection in topic.get("connections", []):
                        entity_name = connection.get("entity")
                        if any(e["name"] == entity_name for e in notebook["entities"]):
                            # Add topic to notebook if not already present
                            topic_entry = {
                                "name": topic["name"],
                                "relevance": 0.7,  # Default relevance
                            }
                            if topic_entry not in notebook["topics"]:
                                notebook["topics"].append(topic_entry)

            return list(notebooks.values())

        except Exception as e:
            logger.error(f"Error getting notebooks: {e}")
            return []
