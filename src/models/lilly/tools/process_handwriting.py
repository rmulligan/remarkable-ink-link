#!/usr/bin/env python3
"""Process handwritten notes from reMarkable using Claude's vision capabilities."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional


def create_claude_prompt(image_path: str, content_type: str = "text") -> str:
    """Create a prompt for Claude based on the content type."""
    prompts = {
        "text": """
Please transcribe the handwritten text in this image.
Maintain the formatting structure as much as possible.
If there are multiple sections or paragraphs, preserve them.
If any text is unclear, indicate with [?].
        """,
        "math": """
Please transcribe the mathematical content in this image.
Represent equations using LaTeX notation.
If any symbols are unclear, indicate with [?].
        """,
        "diagram": """
Please describe the diagram or drawing in this image.
Identify key elements, connections, and any labeled components.
If there are annotations or labels, transcribe them.
        """,
        "mixed": """
Please analyze this handwritten note which contains mixed content (text, diagrams, etc.).
1. Transcribe all text, maintaining the original formatting.
2. Describe any diagrams, drawings, or non-text elements.
3. Preserve the spatial relationships between different elements.
4. If any content is unclear, indicate with [?].
        """,
    }

    # Default to mixed if content type not recognized
    prompt = prompts.get(content_type.lower(), prompts["mixed"])

    # Construct the full command for Claude
    return f"""
I'm going to show you an image of a handwritten note from a reMarkable tablet.

{prompt}

After transcribing, please also:
1. Identify any key concepts, entities, or topics mentioned
2. Extract any tasks or action items
3. Note any questions or areas that need further exploration
    """


def run_claude_command(prompt: str, image_path: str) -> str:
    """Run a command using Claude CLI with an image and return the result."""
    try:
        # Create a temporary file with the prompt
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp:
            temp.write(prompt)
            temp_path = temp.name

        # Run Claude with the image and prompt
        cmd = ["claude", image_path, "--prompt-file", temp_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Clean up the temporary file
        os.unlink(temp_path)

        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running Claude command: {e}")
        print(f"Error output: {e.stderr}")
        return ""


def extract_knowledge_entities(transcription: str) -> List[Dict[str, Any]]:
    """Extract knowledge entities from the transcription using Claude."""
    prompt = f"""
Based on the following transcription of a handwritten note, please identify all entities, concepts, and relationships.
Format the output as a JSON array with objects containing:
- "name": The entity name
- "entityType": The type (Concept, Person, Place, Organization, Task, etc.)
- "mentions": List of exact text snippets from the transcription that reference this entity

Here's the transcription:

{transcription}

Only respond with the JSON array, nothing else.
    """

    try:
        result = subprocess.run(
            ["claude"],
            input=prompt.encode(),
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse the JSON response
        output = result.stdout.strip()
        # Find JSON array in the output (Claude might add extra text)
        start_idx = output.find("[")
        end_idx = output.rfind("]") + 1

        if start_idx >= 0 and end_idx > start_idx:
            json_str = output[start_idx:end_idx]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                print("Error: Could not parse JSON from Claude's response")
                return []
        else:
            print("Error: No JSON array found in Claude's response")
            return []

    except subprocess.CalledProcessError as e:
        print(f"Error using Claude to extract entities: {e}")
        print(f"Error output: {e.stderr}")
        return []


def extract_relationships(
    transcription: str, entities: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Extract relationships between entities in the transcription using Claude."""
    # Create a list of entity names to help Claude
    entity_list = [f"{e['name']} ({e['entityType']})" for e in entities]
    entity_list_str = "\n".join(entity_list)

    prompt = f"""
Based on the following transcription and list of extracted entities, identify meaningful relationships between these entities.
Format the output as a JSON array with objects containing:
- "from": The name of the source entity
- "to": The name of the target entity
- "relationType": The type of relationship (e.g., MENTIONS, PART_OF, DEPENDS_ON, etc.)

Transcription:
{transcription}

Extracted entities:
{entity_list_str}

Only respond with the JSON array, nothing else.
    """

    try:
        result = subprocess.run(
            ["claude"],
            input=prompt.encode(),
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse the JSON response
        output = result.stdout.strip()
        # Find JSON array in the output
        start_idx = output.find("[")
        end_idx = output.rfind("]") + 1

        if start_idx >= 0 and end_idx > start_idx:
            json_str = output[start_idx:end_idx]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                print("Error: Could not parse JSON from Claude's response")
                return []
        else:
            print("Error: No JSON array found in Claude's response")
            return []

    except subprocess.CalledProcessError as e:
        print(f"Error using Claude to extract relationships: {e}")
        print(f"Error output: {e.stderr}")
        return []


def save_to_knowledge_graph(
    entities: List[Dict[str, Any]], relationships: List[Dict[str, Any]]
) -> None:
    """Save extracted entities and relationships to the knowledge graph."""
    # Format entities for the knowledge graph
    kg_entities = []
    for entity in entities:
        # Convert mentions to observations
        observations = entity.get("mentions", [])
        kg_entities.append(
            {
                "name": entity["name"],
                "entityType": entity["entityType"],
                "observations": observations,
            }
        )

    # Create entities in the knowledge graph using Claude
    if kg_entities:
        entities_json = json.dumps(kg_entities)
        prompt = f"""
Using the neo4j-knowledge MCP tool, please create the following entities:
{entities_json}
        """

        print(f"Adding {len(kg_entities)} entities to the knowledge graph...")
        subprocess.run(
            ["claude"], input=prompt.encode(), capture_output=True, text=True
        )

    # Create relationships in the knowledge graph
    if relationships:
        relationships_json = json.dumps(relationships)
        prompt = f"""
Using the neo4j-knowledge MCP tool, please create the following relations:
{relationships_json}
        """

        print(f"Adding {len(relationships)} relationships to the knowledge graph...")
        subprocess.run(
            ["claude"], input=prompt.encode(), capture_output=True, text=True
        )


def save_transcription(transcription: str, output_path: str) -> None:
    """Save the transcription to a file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcription)
    print(f"Transcription saved to {output_path}")


def main():
    """Main function to process handwritten notes."""
    parser = argparse.ArgumentParser(
        description="Process handwritten notes using Claude vision"
    )
    parser.add_argument("image_path", help="Path to the image of handwritten notes")
    parser.add_argument(
        "--content-type",
        choices=["text", "math", "diagram", "mixed"],
        default="mixed",
        help="Type of content in the image",
    )
    parser.add_argument("--output", help="Path to save the transcription")
    parser.add_argument("--kg", action="store_true", help="Save to knowledge graph")
    args = parser.parse_args()

    # Check if image exists
    if not os.path.exists(args.image_path):
        print(f"Error: Image not found at {args.image_path}")
        sys.exit(1)

    # Process the image with Claude
    prompt = create_claude_prompt(args.image_path, args.content_type)
    print(f"Processing {args.image_path} as {args.content_type} content...")
    transcription = run_claude_command(prompt, args.image_path)

    # Save transcription if output path provided
    if args.output:
        save_transcription(transcription, args.output)
    else:
        print("\nTranscription result:")
        print("-" * 40)
        print(transcription)
        print("-" * 40)

    # Save to knowledge graph if requested
    if args.kg:
        print("Extracting entities and relationships for knowledge graph...")
        entities = extract_knowledge_entities(transcription)
        relationships = extract_relationships(transcription, entities)
        save_to_knowledge_graph(entities, relationships)
        print("Knowledge graph updated.")


if __name__ == "__main__":
    main()
