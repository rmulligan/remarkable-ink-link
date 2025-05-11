"""
Knowledge Graph Service for InkLink.

This service provides an interface to the Neo4j knowledge graph, allowing
for storage and retrieval of entities, relationships, and semantic connections.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from datetime import datetime

import neo4j
from neo4j import GraphDatabase

from inklink.utils.common import sanitize_filename

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """
    Service for interacting with the Neo4j knowledge graph.

    This service provides a facade for Neo4j operations, abstracting the
    complexity of graph database queries and enabling semantic knowledge
    management for InkLink.
    """

    def __init__(
        self,
        uri: str,
        username: str,
        password: str,
        database: str = "neo4j",
    ):
        """
        Initialize the knowledge graph service.

        Args:
            uri: URI of the Neo4j server
            username: Username for Neo4j authentication
            password: Password for Neo4j authentication
            database: Name of the Neo4j database to use
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database

        # Initialize driver
        self._driver = None
        self._initialize_driver()

    def _initialize_driver(self):
        """Initialize the Neo4j driver."""
        try:
            self._driver = GraphDatabase.driver(
                self.uri, auth=(self.username, self.password)
            )
            logger.info("Neo4j driver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {str(e)}")
            self._driver = None

    def close(self):
        """Close the Neo4j driver."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def create_entity(
        self, name: str, entity_type: str, properties: Dict[str, Any] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a new entity in the knowledge graph.

        Args:
            name: Name of the entity
            entity_type: Type of the entity
            properties: Additional properties for the entity

        Returns:
            Tuple of (success, entity_dict)
        """
        if not self._driver:
            logger.error("Neo4j driver not initialized")
            return False, {"error": "Neo4j driver not initialized"}

        # Merge properties if provided
        props = {"name": name, "type": entity_type}
        if properties:
            props.update(properties)

        try:
            with self._driver.session(database=self.database) as session:
                result = session.write_transaction(self._create_entity_tx, props)

                return True, {"id": result["id"], "name": name, "type": entity_type}

        except Exception as e:
            logger.error(f"Error creating entity: {str(e)}")
            return False, {"error": str(e)}

    def _create_entity_tx(self, tx, properties):
        """
        Neo4j transaction function for creating an entity.

        Args:
            tx: Neo4j transaction
            properties: Entity properties

        Returns:
            Entity ID
        """
        query = """
        MERGE (e:Entity {name: $name, type: $type})
        ON CREATE SET e += $properties, e.created = datetime()
        ON MATCH SET e += $properties, e.updated = datetime()
        RETURN id(e) as id
        """

        result = tx.run(
            query,
            name=properties["name"],
            type=properties["type"],
            properties=properties,
        )
        record = result.single()
        return {"id": record["id"]}

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
        if not self._driver:
            logger.error("Neo4j driver not initialized")
            return []

        try:
            with self._driver.session(database=self.database) as session:
                if types:
                    # Filter by specified types
                    result = session.read_transaction(
                        self._get_entities_by_types_tx, types, min_references
                    )
                else:
                    # Get all entities
                    result = session.read_transaction(
                        self._get_all_entities_tx, min_references
                    )

                return result

        except Exception as e:
            logger.error(f"Error getting entities: {str(e)}")
            return []

    def _get_entities_by_types_tx(self, tx, types, min_references):
        """
        Neo4j transaction function for getting entities by type.

        Args:
            tx: Neo4j transaction
            types: List of entity types to filter by
            min_references: Minimum number of references

        Returns:
            List of entity dictionaries
        """
        query = """
        MATCH (e:Entity)
        WHERE e.type IN $types
        WITH e, size((e)<-[:REFERS_TO]-()) as refCount
        WHERE refCount >= $min_references
        OPTIONAL MATCH (e)<-[r:REFERS_TO]-(ref)
        RETURN e, collect(distinct {notebook: ref.notebook, page: ref.page, context: ref.context}) as references
        """

        result = tx.run(query, types=types, min_references=min_references)

        entities = []
        for record in result:
            entity = dict(record["e"])
            entity["references"] = record["references"]
            entities.append(entity)

        return entities

    def _get_all_entities_tx(self, tx, min_references):
        """
        Neo4j transaction function for getting all entities.

        Args:
            tx: Neo4j transaction
            min_references: Minimum number of references

        Returns:
            List of entity dictionaries
        """
        query = """
        MATCH (e:Entity)
        WITH e, size((e)<-[:REFERS_TO]-()) as refCount
        WHERE refCount >= $min_references
        OPTIONAL MATCH (e)<-[r:REFERS_TO]-(ref)
        RETURN e, collect(distinct {notebook: ref.notebook, page: ref.page, context: ref.context}) as references
        """

        result = tx.run(query, min_references=min_references)

        entities = []
        for record in result:
            entity = dict(record["e"])
            entity["references"] = record["references"]
            entities.append(entity)

        return entities

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
        if not self._driver:
            logger.error("Neo4j driver not initialized")
            return []

        try:
            with self._driver.session(database=self.database) as session:
                result = session.read_transaction(
                    self._get_topics_tx, limit, min_connections
                )

                return result

        except Exception as e:
            logger.error(f"Error getting topics: {str(e)}")
            return []

    def _get_topics_tx(self, tx, limit, min_connections):
        """
        Neo4j transaction function for getting topics.

        Args:
            tx: Neo4j transaction
            limit: Maximum number of topics to return
            min_connections: Minimum number of connections

        Returns:
            List of topic dictionaries
        """
        query = """
        MATCH (t:Topic)
        WITH t, size((t)-[:INCLUDES]->()) as connCount
        WHERE connCount >= $min_connections
        OPTIONAL MATCH (t)-[r:INCLUDES]->(e:Entity)
        RETURN t,
               collect(distinct {entity: e.name, entity_type: e.type, strength: r.strength}) as connections
        ORDER BY connCount DESC
        LIMIT $limit
        """

        result = tx.run(query, limit=limit, min_connections=min_connections)

        topics = []
        for record in result:
            topic = dict(record["t"])
            topic["connections"] = record["connections"]
            topics.append(topic)

        return topics

    def get_notebooks(self) -> List[Dict[str, Any]]:
        """
        Get notebooks from the knowledge graph.

        Returns:
            List of notebook dictionaries with their entities and topics
        """
        if not self._driver:
            logger.error("Neo4j driver not initialized")
            return []

        try:
            with self._driver.session(database=self.database) as session:
                result = session.read_transaction(self._get_notebooks_tx)
                return result

        except Exception as e:
            logger.error(f"Error getting notebooks: {str(e)}")
            return []

    def _get_notebooks_tx(self, tx):
        """
        Neo4j transaction function for getting notebooks.

        Args:
            tx: Neo4j transaction

        Returns:
            List of notebook dictionaries
        """
        query = """
        MATCH (n:Notebook)
        OPTIONAL MATCH (n)-[r:CONTAINS]->(e:Entity)
        WITH n, collect(distinct {name: e.name, type: e.type, count: r.count}) as entities
        OPTIONAL MATCH (n)-[rt:RELATES_TO]->(t:Topic)
        RETURN n,
               entities,
               collect(distinct {name: t.name, relevance: rt.relevance}) as topics
        """

        result = tx.run(query)

        notebooks = []
        for record in result:
            notebook = dict(record["n"])
            notebook["entities"] = record["entities"]
            notebook["topics"] = record["topics"]
            notebooks.append(notebook)

        return notebooks

    def add_entity_reference(
        self,
        entity_name: str,
        entity_type: str,
        notebook_name: str,
        page_number: Union[int, str],
        context: str = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Add a reference to an entity from a notebook page.

        Args:
            entity_name: Name of the entity
            entity_type: Type of the entity
            notebook_name: Name of the notebook
            page_number: Page number in the notebook
            context: Context surrounding the reference

        Returns:
            Tuple of (success, reference_dict)
        """
        if not self._driver:
            logger.error("Neo4j driver not initialized")
            return False, {"error": "Neo4j driver not initialized"}

        try:
            with self._driver.session(database=self.database) as session:
                result = session.write_transaction(
                    self._add_entity_reference_tx,
                    entity_name,
                    entity_type,
                    notebook_name,
                    page_number,
                    context,
                )

                return True, result

        except Exception as e:
            logger.error(f"Error adding entity reference: {str(e)}")
            return False, {"error": str(e)}

    def _add_entity_reference_tx(
        self, tx, entity_name, entity_type, notebook_name, page_number, context
    ):
        """
        Neo4j transaction function for adding an entity reference.

        Args:
            tx: Neo4j transaction
            entity_name: Name of the entity
            entity_type: Type of the entity
            notebook_name: Name of the notebook
            page_number: Page number in the notebook
            context: Context surrounding the reference

        Returns:
            Reference dictionary
        """
        # Ensure entity exists
        entity_query = """
        MERGE (e:Entity {name: $name, type: $type})
        ON CREATE SET e.created = datetime()
        RETURN id(e) as entity_id
        """

        entity_result = tx.run(entity_query, name=entity_name, type=entity_type)
        entity_record = entity_result.single()
        entity_id = entity_record["entity_id"]

        # Ensure notebook exists
        notebook_query = """
        MERGE (n:Notebook {name: $name})
        ON CREATE SET n.created = datetime()
        RETURN id(n) as notebook_id
        """

        notebook_result = tx.run(notebook_query, name=notebook_name)
        notebook_record = notebook_result.single()
        notebook_id = notebook_record["notebook_id"]

        # Create reference
        reference_query = """
        MATCH (e:Entity), (n:Notebook)
        WHERE id(e) = $entity_id AND id(n) = $notebook_id
        MERGE (ref:Reference {notebook: $notebook, page: $page})
        ON CREATE SET ref.created = datetime(), ref.context = $context
        ON MATCH SET ref.context = $context, ref.updated = datetime()
        MERGE (ref)-[:REFERS_TO]->(e)
        MERGE (n)-[:CONTAINS]->(e)
        ON CREATE SET n.page_count = coalesce(n.page_count, 0) + 1
        RETURN id(ref) as reference_id
        """

        reference_result = tx.run(
            reference_query,
            entity_id=entity_id,
            notebook_id=notebook_id,
            notebook=notebook_name,
            page=str(page_number),
            context=context,
        )
        reference_record = reference_result.single()
        reference_id = reference_record["reference_id"]

        # Update entity count in notebook
        count_query = """
        MATCH (n:Notebook {name: $notebook})-[r:CONTAINS]->(e:Entity {name: $entity})
        SET r.count = coalesce(r.count, 0) + 1
        """

        tx.run(count_query, notebook=notebook_name, entity=entity_name)

        return {
            "reference_id": reference_id,
            "entity_id": entity_id,
            "notebook_id": notebook_id,
            "entity": entity_name,
            "notebook": notebook_name,
            "page": page_number,
        }

    def create_semantic_connection(
        self,
        entity1_name: str,
        entity2_name: str,
        strength: float = 0.5,
        relation_type: str = "SEMANTICALLY_RELATED",
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a semantic connection between two entities.

        Args:
            entity1_name: Name of the first entity
            entity2_name: Name of the second entity
            strength: Strength of the connection (0.0 to 1.0)
            relation_type: Type of the relation

        Returns:
            Tuple of (success, connection_dict)
        """
        if not self._driver:
            logger.error("Neo4j driver not initialized")
            return False, {"error": "Neo4j driver not initialized"}

        try:
            with self._driver.session(database=self.database) as session:
                result = session.write_transaction(
                    self._create_semantic_connection_tx,
                    entity1_name,
                    entity2_name,
                    strength,
                    relation_type,
                )

                return True, result

        except Exception as e:
            logger.error(f"Error creating semantic connection: {str(e)}")
            return False, {"error": str(e)}

    def _create_semantic_connection_tx(
        self, tx, entity1_name, entity2_name, strength, relation_type
    ):
        """
        Neo4j transaction function for creating a semantic connection.

        Args:
            tx: Neo4j transaction
            entity1_name: Name of the first entity
            entity2_name: Name of the second entity
            strength: Strength of the connection
            relation_type: Type of the relation

        Returns:
            Connection dictionary
        """
        query = (
            """
        MATCH (e1:Entity {name: $entity1})
        MATCH (e2:Entity {name: $entity2})
        MERGE (e1)-[r:%s {strength: $strength}]->(e2)
        ON CREATE SET r.created = datetime()
        ON MATCH SET r.strength = $strength, r.updated = datetime()
        RETURN id(r) as connection_id
        """
            % relation_type
        )

        result = tx.run(
            query, entity1=entity1_name, entity2=entity2_name, strength=strength
        )
        record = result.single()

        return {
            "connection_id": record["connection_id"],
            "entity1": entity1_name,
            "entity2": entity2_name,
            "strength": strength,
            "relation_type": relation_type,
        }

    def create_topic(
        self, name: str, description: str = None, entities: List[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a topic and connect it to entities.

        Args:
            name: Name of the topic
            description: Description of the topic
            entities: List of entity dictionaries with name and strength

        Returns:
            Tuple of (success, topic_dict)
        """
        if not self._driver:
            logger.error("Neo4j driver not initialized")
            return False, {"error": "Neo4j driver not initialized"}

        try:
            with self._driver.session(database=self.database) as session:
                result = session.write_transaction(
                    self._create_topic_tx, name, description, entities
                )

                return True, result

        except Exception as e:
            logger.error(f"Error creating topic: {str(e)}")
            return False, {"error": str(e)}

    def _create_topic_tx(self, tx, name, description, entities):
        """
        Neo4j transaction function for creating a topic.

        Args:
            tx: Neo4j transaction
            name: Name of the topic
            description: Description of the topic
            entities: List of entity dictionaries

        Returns:
            Topic dictionary
        """
        # Create topic node
        topic_query = """
        MERGE (t:Topic {name: $name})
        ON CREATE SET t.created = datetime(), t.description = $description
        ON MATCH SET t.description = $description, t.updated = datetime()
        RETURN id(t) as topic_id
        """

        topic_result = tx.run(topic_query, name=name, description=description)
        topic_record = topic_result.single()
        topic_id = topic_record["topic_id"]

        # Connect topic to entities if provided
        entity_connections = []
        if entities:
            for entity in entities:
                entity_name = entity.get("name")
                strength = entity.get("strength", 0.5)

                # Connect topic to entity
                connection_query = """
                MATCH (t:Topic), (e:Entity)
                WHERE id(t) = $topic_id AND e.name = $entity
                MERGE (t)-[r:INCLUDES]->(e)
                ON CREATE SET r.strength = $strength, r.created = datetime()
                ON MATCH SET r.strength = $strength, r.updated = datetime()
                RETURN id(r) as connection_id
                """

                connection_result = tx.run(
                    connection_query,
                    topic_id=topic_id,
                    entity=entity_name,
                    strength=strength,
                )
                connection_record = connection_result.single()

                entity_connections.append(
                    {
                        "entity": entity_name,
                        "strength": strength,
                        "connection_id": connection_record["connection_id"],
                    }
                )

        return {
            "topic_id": topic_id,
            "name": name,
            "description": description,
            "connections": entity_connections,
        }

    def relate_notebook_to_topic(
        self, notebook_name: str, topic_name: str, relevance: float = 0.5
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a relationship between a notebook and a topic.

        Args:
            notebook_name: Name of the notebook
            topic_name: Name of the topic
            relevance: Relevance score (0.0 to 1.0)

        Returns:
            Tuple of (success, relation_dict)
        """
        if not self._driver:
            logger.error("Neo4j driver not initialized")
            return False, {"error": "Neo4j driver not initialized"}

        try:
            with self._driver.session(database=self.database) as session:
                result = session.write_transaction(
                    self._relate_notebook_to_topic_tx,
                    notebook_name,
                    topic_name,
                    relevance,
                )

                return True, result

        except Exception as e:
            logger.error(f"Error relating notebook to topic: {str(e)}")
            return False, {"error": str(e)}

    def _relate_notebook_to_topic_tx(self, tx, notebook_name, topic_name, relevance):
        """
        Neo4j transaction function for relating a notebook to a topic.

        Args:
            tx: Neo4j transaction
            notebook_name: Name of the notebook
            topic_name: Name of the topic
            relevance: Relevance score

        Returns:
            Relation dictionary
        """
        query = """
        MATCH (n:Notebook {name: $notebook})
        MATCH (t:Topic {name: $topic})
        MERGE (n)-[r:RELATES_TO]->(t)
        ON CREATE SET r.relevance = $relevance, r.created = datetime()
        ON MATCH SET r.relevance = $relevance, r.updated = datetime()
        RETURN id(r) as relation_id
        """

        result = tx.run(
            query, notebook=notebook_name, topic=topic_name, relevance=relevance
        )
        record = result.single()

        return {
            "relation_id": record["relation_id"],
            "notebook": notebook_name,
            "topic": topic_name,
            "relevance": relevance,
        }
