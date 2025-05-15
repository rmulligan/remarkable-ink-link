#!/usr/bin/env python3
"""
Initialize the knowledge graph for Lilly.
Creates basic entity types and relationships for reMarkable notes management.
"""

import json
import os
import subprocess
import sys
from typing import Any, Dict, List

# Define the knowledge graph structure
ENTITY_TYPES = [
    "Note",  # A handwritten note or page
    "Notebook",  # A collection of notes
    "Concept",  # An abstract idea or topic
    "Entity",  # A named entity (person, place, organization)
    "Task",  # An action item or to-do
    "Project",  # A collection of related tasks
    "Tag",  # A user-defined categorization
    "Document",  # A reference document
    "Image",  # A visual element or diagram
    "Link",  # A connection to external content
]

RELATIONSHIP_TYPES = [
    "CONTAINS",  # Notebook CONTAINS Note
    "MENTIONS",  # Note MENTIONS Concept
    "RELATED_TO",  # Concept RELATED_TO Concept
    "TAGGED_WITH",  # Note TAGGED_WITH Tag
    "PART_OF",  # Task PART_OF Project
    "REFERENCES",  # Note REFERENCES Document
    "CREATED_ON",  # Note CREATED_ON Date
    "MODIFIED_ON",  # Note MODIFIED_ON Date
    "DEPICTS",  # Image DEPICTS Concept
    "LINKS_TO",  # Link LINKS_TO Document
    "DEPENDS_ON",  # Task DEPENDS_ON Task
    "AUTHORED_BY",  # Note AUTHORED_BY Person
    "CONNECTED_TO",  # Note CONNECTED_TO Note
]


def run_claude_command(command: str) -> str:
    """Run a command using Claude CLI and return the result."""
    try:
        result = subprocess.run(
            ["claude"],
            input=command.encode(),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running Claude command: {e}")
        print(f"Error output: {e.stderr}")
        return ""


def create_entity_types(entity_types: List[str]) -> None:
    """Create entity types in the knowledge graph."""
    entities_json = json.dumps(
        [{"name": et, "entityType": "EntityType"} for et in entity_types]
    )

    command = f"""
Using the neo4j-knowledge MCP tool, please create the following entity types:
{entities_json}

These represent the fundamental entity types for Lilly's knowledge graph.
"""

    print("Creating entity types...")
    run_claude_command(command)


def create_relationship_types(relationship_types: List[str]) -> None:
    """Create relationship types in the knowledge graph."""
    # First create a RelationshipType entity type if it doesn't exist
    command = """
Using the neo4j-knowledge MCP tool, please create an entity type for relationships:
[{"name": "RelationshipType", "entityType": "EntityType"}]
"""
    run_claude_command(command)

    # Now create each relationship type
    rel_json = json.dumps(
        [{"name": rt, "entityType": "RelationshipType"} for rt in relationship_types]
    )

    command = f"""
Using the neo4j-knowledge MCP tool, please create the following relationship types:
{rel_json}

These represent the fundamental relationship types for Lilly's knowledge graph.
"""

    print("Creating relationship types...")
    run_claude_command(command)


def initialize_graph() -> None:
    """Initialize the knowledge graph with entity and relationship types."""
    # First switch to the Lilly knowledge graph
    command = """
Using the neo4j-knowledge MCP tool, please switch to a database named "lilly_knowledge"
and create it if it doesn't exist. Then, confirm the current database name.
"""
    print("Switching to Lilly's knowledge graph database...")
    run_claude_command(command)

    # Create entity types
    create_entity_types(ENTITY_TYPES)

    # Create relationship types
    create_relationship_types(RELATIONSHIP_TYPES)

    print("Knowledge graph initialization complete.")


if __name__ == "__main__":
    print("Initializing Lilly's knowledge graph...")
    initialize_graph()
    print("Done.")
