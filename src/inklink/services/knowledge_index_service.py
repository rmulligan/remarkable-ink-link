"""
Knowledge Index Service for InkLink.

This service creates knowledge index notebooks in EPUB format,
organizing entities, topics, and notebook references for easy navigation.
"""

import os
import re
import logging
import tempfile
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime

from inklink.services.epub_generator import EPUBGenerator
from inklink.services.knowledge_graph_service import KnowledgeGraphService
from inklink.adapters.remarkable_adapter import RemarkableAdapter

logger = logging.getLogger(__name__)


class KnowledgeIndexService:
    """
    Service for creating knowledge index notebooks.

    This service generates different types of index notebooks:
    - Entity Index: lists entities grouped by type with references
    - Topic Index: lists topics with connected entities
    - Notebook Index: lists notebooks with their content summaries
    - Master Index: combines all of the above

    All indexes are generated in EPUB format with hyperlinks for navigation.
    """

    def __init__(
        self,
        knowledge_graph_service: KnowledgeGraphService,
        epub_generator: EPUBGenerator,
        remarkable_adapter: RemarkableAdapter,
        output_dir: str = None,
    ):
        """
        Initialize the knowledge index service.

        Args:
            knowledge_graph_service: Service for working with the knowledge graph
            epub_generator: Service for generating EPUB documents
            remarkable_adapter: Adapter for uploading to reMarkable
            output_dir: Directory to save generated index notebooks
        """
        self.kg_service = knowledge_graph_service
        self.epub_generator = epub_generator
        self.remarkable_adapter = remarkable_adapter
        self.output_dir = output_dir or tempfile.gettempdir()

        # EPUB format is inherent, not a configuration option
        self.use_epub_format = True

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def create_entity_index(
        self,
        entity_types: Optional[List[str]] = None,
        min_references: int = 1,
        upload_to_remarkable: bool = True,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create an entity index notebook grouping entities by type.

        Args:
            entity_types: Optional list of entity types to include (None for all)
            min_references: Minimum number of references for an entity to be included
            upload_to_remarkable: Whether to upload index to reMarkable Cloud

        Returns:
            Tuple of (success, result_dict)
        """
        logger.info(
            f"Creating entity index with types={entity_types}, min_refs={min_references}"
        )

        try:
            # Get entities from knowledge graph
            entities = self.kg_service.get_entities(types=entity_types)

            # Filter by minimum references
            filtered_entities = [
                e for e in entities if len(e.get("references", [])) >= min_references
            ]

            if not filtered_entities:
                logger.warning("No entities match criteria for index")
                return False, {"error": "No entities match criteria"}

            # Create entity index content
            content = self._generate_entity_index_content(filtered_entities)

            # Generate EPUB document
            title = f"Entity Index - {datetime.now().strftime('%Y-%m-%d')}"
            success, result = self.epub_generator.create_epub_from_markdown(
                title=title,
                content=content,
                author="InkLink Knowledge Graph",
                metadata={"description": "Index of entities from knowledge graph"},
            )

            if not success:
                return False, result

            # Optionally upload to reMarkable
            if upload_to_remarkable:
                upload_success, upload_result = self._upload_to_remarkable(
                    result["path"], title
                )
                result["upload_result"] = {
                    "success": upload_success,
                    "message": upload_result,
                    "title": title,
                }

            # Add additional info to result
            result["entity_count"] = len(filtered_entities)
            result["entity_types"] = list(
                set(e.get("type", "Other") for e in filtered_entities)
            )

            return True, result

        except Exception as e:
            logger.error(f"Error creating entity index: {str(e)}")
            return False, {"error": str(e)}

    def create_topic_index(
        self,
        top_n_topics: int = 20,
        min_connections: int = 2,
        upload_to_remarkable: bool = True,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a topic index notebook organizing content by topic.

        Args:
            top_n_topics: Number of top topics to include
            min_connections: Minimum connections for a topic to be included
            upload_to_remarkable: Whether to upload index to reMarkable Cloud

        Returns:
            Tuple of (success, result_dict)
        """
        logger.info(
            f"Creating topic index with top_n={top_n_topics}, min_conn={min_connections}"
        )

        try:
            # Get topics from knowledge graph
            topics = self.kg_service.get_topics(
                limit=top_n_topics, min_connections=min_connections
            )

            if not topics:
                logger.warning("No topics match criteria for index")
                return False, {"error": "No topics match criteria"}

            # Create topic index content
            content = self._generate_topic_index_content(topics)

            # Generate EPUB document
            title = f"Topic Index - {datetime.now().strftime('%Y-%m-%d')}"
            success, result = self.epub_generator.create_epub_from_markdown(
                title=title,
                content=content,
                author="InkLink Knowledge Graph",
                metadata={"description": "Index of topics from knowledge graph"},
            )

            if not success:
                return False, result

            # Optionally upload to reMarkable
            if upload_to_remarkable:
                upload_success, upload_result = self._upload_to_remarkable(
                    result["path"], title
                )
                result["upload_result"] = {
                    "success": upload_success,
                    "message": upload_result,
                    "title": title,
                }

            # Add additional info to result
            result["topic_count"] = len(topics)

            return True, result

        except Exception as e:
            logger.error(f"Error creating topic index: {str(e)}")
            return False, {"error": str(e)}

    def create_notebook_index(
        self,
        upload_to_remarkable: bool = True,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a notebook index organizing content by source notebook.

        Args:
            upload_to_remarkable: Whether to upload index to reMarkable Cloud

        Returns:
            Tuple of (success, result_dict)
        """
        logger.info("Creating notebook index")

        try:
            # Get notebooks from knowledge graph
            notebooks = self.kg_service.get_notebooks()

            if not notebooks:
                logger.warning("No notebooks found for index")
                return False, {"error": "No notebooks found"}

            # Create notebook index content
            content = self._generate_notebook_index_content(notebooks)

            # Generate EPUB document
            title = f"Notebook Index - {datetime.now().strftime('%Y-%m-%d')}"
            success, result = self.epub_generator.create_epub_from_markdown(
                title=title,
                content=content,
                author="InkLink Knowledge Graph",
                metadata={"description": "Index of notebooks and their content"},
            )

            if not success:
                return False, result

            # Optionally upload to reMarkable
            if upload_to_remarkable:
                upload_success, upload_result = self._upload_to_remarkable(
                    result["path"], title
                )
                result["upload_result"] = {
                    "success": upload_success,
                    "message": upload_result,
                    "title": title,
                }

            # Add additional info to result
            result["notebook_count"] = len(notebooks)

            return True, result

        except Exception as e:
            logger.error(f"Error creating notebook index: {str(e)}")
            return False, {"error": str(e)}

    def create_master_index(
        self,
        upload_to_remarkable: bool = True,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a master index combining entity, topic, and notebook indices.

        Args:
            upload_to_remarkable: Whether to upload index to reMarkable Cloud

        Returns:
            Tuple of (success, result_dict)
        """
        logger.info("Creating master index")

        try:
            # Get data for all three index types
            entities = self.kg_service.get_entities(min_references=1)
            topics = self.kg_service.get_topics(limit=50, min_connections=2)
            notebooks = self.kg_service.get_notebooks()

            if not entities and not topics and not notebooks:
                logger.warning("No data found for master index")
                return False, {"error": "No data found for index"}

            # Create master index content
            content = self._generate_master_index_content(entities, topics, notebooks)

            # Generate EPUB document
            title = f"Knowledge Index - {datetime.now().strftime('%Y-%m-%d')}"
            success, result = self.epub_generator.create_epub_from_markdown(
                title=title,
                content=content,
                author="InkLink Knowledge Graph",
                metadata={"description": "Master index of knowledge graph content"},
            )

            if not success:
                return False, result

            # Optionally upload to reMarkable
            if upload_to_remarkable:
                upload_success, upload_result = self._upload_to_remarkable(
                    result["path"], title
                )
                result["upload_result"] = {
                    "success": upload_success,
                    "message": upload_result,
                    "title": title,
                }

            # Add additional info to result
            result["entity_count"] = len(entities)
            result["topic_count"] = len(topics)
            result["notebook_count"] = len(notebooks)

            return True, result

        except Exception as e:
            logger.error(f"Error creating master index: {str(e)}")
            return False, {"error": str(e)}

    def _generate_entity_index_content(self, entities: List[Dict[str, Any]]) -> str:
        """
        Generate markdown content for entity index.

        Args:
            entities: List of entity dictionaries

        Returns:
            Markdown formatted content
        """
        # Create entity index structure
        content = "# Entity Index\n\n"
        content += "This index organizes entities by type, showing all references.\n\n"

        # Group entities by type
        entities_by_type = {}
        for entity in entities:
            entity_type = entity.get("type", "Other")
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)

        # Create anchor IDs for all entities for linking
        entity_anchors = {}
        for entity in entities:
            name = entity.get("name", "")
            anchor_id = self._create_anchor_id(name)
            entity_anchors[name] = anchor_id

        # Generate content for each entity type
        for entity_type, type_entities in sorted(entities_by_type.items()):
            content += f"## {entity_type}s\n\n"

            # Sort entities by name
            sorted_entities = sorted(type_entities, key=lambda e: e.get("name", ""))

            # Add each entity
            for entity in sorted_entities:
                name = entity.get("name", "")
                anchor_id = entity_anchors[name]
                references = entity.get("references", [])

                content += f"### <a id='{anchor_id}'></a>{name}\n\n"

                if entity.get("description"):
                    content += f"{entity.get('description')}\n\n"

                if references:
                    content += "**References:**\n\n"

                    # Group references by notebook
                    refs_by_notebook = {}
                    for ref in references:
                        notebook = ref.get("notebook", "Unknown")
                        if notebook not in refs_by_notebook:
                            refs_by_notebook[notebook] = []
                        refs_by_notebook[notebook].append(ref)

                    # Add references grouped by notebook
                    for notebook, refs in sorted(refs_by_notebook.items()):
                        content += f"* **{notebook}**:\n"
                        for ref in refs:
                            page = ref.get("page", "")
                            context = ref.get("context", "")
                            content += f"  * Page {page}"
                            if context:
                                content += f": {context[:100]}..."
                            content += "\n"

                    content += "\n"

        return content

    def _generate_topic_index_content(self, topics: List[Dict[str, Any]]) -> str:
        """
        Generate markdown content for topic index.

        Args:
            topics: List of topic dictionaries

        Returns:
            Markdown formatted content
        """
        # Create topic index structure
        content = "# Topic Index\n\n"
        content += "This index organizes content by topic, showing related entities and connections.\n\n"

        # Create anchor IDs for all topics for linking
        topic_anchors = {}
        for topic in topics:
            name = topic.get("name", "")
            anchor_id = self._create_anchor_id(name)
            topic_anchors[name] = anchor_id

        # Generate TOC
        content += "## Topics\n\n"
        for topic in sorted(topics, key=lambda t: t.get("name", "")):
            name = topic.get("name", "")
            connection_count = len(topic.get("connections", []))
            content += (
                f"- [{name}](#{topic_anchors[name]}) ({connection_count} connections)\n"
            )

        content += "\n## Topic Details\n\n"

        # Generate content for each topic
        for topic in sorted(topics, key=lambda t: t.get("name", "")):
            name = topic.get("name", "")
            anchor_id = topic_anchors[name]
            connections = topic.get("connections", [])

            content += f"### <a id='{anchor_id}'></a>{name}\n\n"

            if topic.get("description"):
                content += f"{topic.get('description')}\n\n"

            if connections:
                content += "**Connected Entities:**\n\n"

                # Group connections by entity type
                connections_by_type = {}
                for conn in connections:
                    entity_type = conn.get("entity_type", "Other")
                    if entity_type not in connections_by_type:
                        connections_by_type[entity_type] = []
                    connections_by_type[entity_type].append(conn)

                # Add connections grouped by entity type
                for entity_type, conns in sorted(connections_by_type.items()):
                    content += f"* **{entity_type}s**:\n"
                    for conn in sorted(conns, key=lambda c: c.get("entity", "")):
                        entity = conn.get("entity", "")
                        strength = conn.get("strength", 0)
                        content += f"  * {entity}"
                        if strength:
                            content += f" (relevance: {strength:.2f})"
                        content += "\n"

                content += "\n"

            if topic.get("notebooks"):
                content += "**Relevant Notebooks:**\n\n"
                for notebook in topic.get("notebooks", []):
                    content += f"* {notebook.get('name', '')}\n"
                content += "\n"

        return content

    def _generate_notebook_index_content(self, notebooks: List[Dict[str, Any]]) -> str:
        """
        Generate markdown content for notebook index.

        Args:
            notebooks: List of notebook dictionaries

        Returns:
            Markdown formatted content
        """
        # Create notebook index structure
        content = "# Notebook Index\n\n"
        content += "This index organizes content by source notebook, showing key entities and topics.\n\n"

        # Create anchor IDs for all notebooks for linking
        notebook_anchors = {}
        for notebook in notebooks:
            name = notebook.get("name", "")
            anchor_id = self._create_anchor_id(name)
            notebook_anchors[name] = anchor_id

        # Generate TOC
        content += "## Notebooks\n\n"
        for notebook in sorted(notebooks, key=lambda n: n.get("name", "")):
            name = notebook.get("name", "")
            page_count = notebook.get("page_count", 0)
            entity_count = len(notebook.get("entities", []))
            content += f"- [{name}](#{notebook_anchors[name]}) ({page_count} pages, {entity_count} entities)\n"

        content += "\n## Notebook Details\n\n"

        # Generate content for each notebook
        for notebook in sorted(notebooks, key=lambda n: n.get("name", "")):
            name = notebook.get("name", "")
            anchor_id = notebook_anchors[name]
            entities = notebook.get("entities", [])
            topics = notebook.get("topics", [])
            summary = notebook.get("summary", "")

            content += f"### <a id='{anchor_id}'></a>{name}\n\n"

            if summary:
                content += f"**Summary:** {summary}\n\n"

            if notebook.get("created_date"):
                content += f"**Created:** {notebook.get('created_date')}\n\n"

            if notebook.get("page_count"):
                content += f"**Pages:** {notebook.get('page_count')}\n\n"

            if entities:
                content += "**Key Entities:**\n\n"

                # Group entities by type
                entities_by_type = {}
                for entity in entities:
                    entity_type = entity.get("type", "Other")
                    if entity_type not in entities_by_type:
                        entities_by_type[entity_type] = []
                    entities_by_type[entity_type].append(entity)

                # Add entities grouped by type
                for entity_type, type_entities in sorted(entities_by_type.items()):
                    content += f"* **{entity_type}s**:\n"
                    for entity in sorted(
                        type_entities, key=lambda e: e.get("name", "")
                    ):
                        name = entity.get("name", "")
                        count = entity.get("count", 1)
                        content += f"  * {name}"
                        if count > 1:
                            content += f" ({count} mentions)"
                        content += "\n"

                content += "\n"

            if topics:
                content += "**Main Topics:**\n\n"
                for topic in sorted(
                    topics, key=lambda t: t.get("relevance", 0), reverse=True
                ):
                    name = topic.get("name", "")
                    relevance = topic.get("relevance", 0)
                    content += f"* {name}"
                    if relevance:
                        content += f" (relevance: {relevance:.2f})"
                    content += "\n"

                content += "\n"

            if notebook.get("pages"):
                content += "**Key Pages:**\n\n"
                for page in sorted(
                    notebook.get("pages", []), key=lambda p: p.get("number", 0)
                ):
                    page_num = page.get("number", 0)
                    title = page.get("title", f"Page {page_num}")
                    summary = page.get("summary", "")
                    content += f"* **Page {page_num}**: {title}\n"
                    if summary:
                        content += f"  * {summary[:100]}...\n"

                content += "\n"

        return content

    def _generate_master_index_content(
        self,
        entities: List[Dict[str, Any]],
        topics: List[Dict[str, Any]],
        notebooks: List[Dict[str, Any]],
    ) -> str:
        """
        Generate markdown content for master index.

        Args:
            entities: List of entity dictionaries
            topics: List of topic dictionaries
            notebooks: List of notebook dictionaries

        Returns:
            Markdown formatted content
        """
        # Create master index structure
        content = "# Knowledge Index\n\n"
        content += "This master index combines entity, topic, and notebook indices for comprehensive navigation.\n\n"

        # Create anchor IDs for linking between sections
        entity_section_id = "entity-index"
        topic_section_id = "topic-index"
        notebook_section_id = "notebook-index"

        # Generate TOC for master index
        content += "## Contents\n\n"
        content += f"1. [Entity Index](#{entity_section_id})\n"
        content += f"2. [Topic Index](#{topic_section_id})\n"
        content += f"3. [Notebook Index](#{notebook_section_id})\n\n"

        # Add Entity Index
        content += f"## <a id='{entity_section_id}'></a>Entity Index\n\n"
        content += f"[Back to Contents](#contents)\n\n"

        # Filter to top entities by reference count
        top_entities = sorted(
            entities, key=lambda e: len(e.get("references", [])), reverse=True
        )[
            :50
        ]  # Limit to 50 most referenced entities

        # Group entities by type
        entities_by_type = {}
        for entity in top_entities:
            entity_type = entity.get("type", "Other")
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)

        # Create anchor IDs for all entities
        entity_anchors = {}
        for entity in top_entities:
            name = entity.get("name", "")
            anchor_id = self._create_anchor_id(f"entity-{name}")
            entity_anchors[name] = anchor_id

        # Generate condensed entity listing by type
        for entity_type, type_entities in sorted(entities_by_type.items()):
            content += f"### {entity_type}s\n\n"

            # Sort entities by reference count
            sorted_entities = sorted(
                type_entities, key=lambda e: len(e.get("references", [])), reverse=True
            )

            # Add each entity with reference count
            for entity in sorted_entities:
                name = entity.get("name", "")
                ref_count = len(entity.get("references", []))
                content += (
                    f"* [{name}](#{entity_anchors[name]}) ({ref_count} references)\n"
                )

            content += "\n"

        # Add Topic Index
        content += f"## <a id='{topic_section_id}'></a>Topic Index\n\n"
        content += f"[Back to Contents](#contents)\n\n"

        # Create anchor IDs for all topics
        topic_anchors = {}
        for topic in topics:
            name = topic.get("name", "")
            anchor_id = self._create_anchor_id(f"topic-{name}")
            topic_anchors[name] = anchor_id

        # Generate condensed topic listing
        content += "### Top Topics\n\n"
        for topic in sorted(
            topics, key=lambda t: len(t.get("connections", [])), reverse=True
        )[:30]:
            name = topic.get("name", "")
            conn_count = len(topic.get("connections", []))
            content += (
                f"* [{name}](#{topic_anchors[name]}) ({conn_count} connections)\n"
            )

        content += "\n"

        # Add Notebook Index
        content += f"## <a id='{notebook_section_id}'></a>Notebook Index\n\n"
        content += f"[Back to Contents](#contents)\n\n"

        # Create anchor IDs for all notebooks
        notebook_anchors = {}
        for notebook in notebooks:
            name = notebook.get("name", "")
            anchor_id = self._create_anchor_id(f"notebook-{name}")
            notebook_anchors[name] = anchor_id

        # Generate condensed notebook listing
        content += "### Notebooks\n\n"
        for notebook in sorted(notebooks, key=lambda n: n.get("name", "")):
            name = notebook.get("name", "")
            entity_count = len(notebook.get("entities", []))
            page_count = notebook.get("page_count", 0)
            content += f"* [{name}](#{notebook_anchors[name]}) ({page_count} pages, {entity_count} entities)\n"

        content += "\n"

        # Add detailed entity sections
        content += "## Entity Details\n\n"
        for entity in top_entities:
            name = entity.get("name", "")
            anchor_id = entity_anchors[name]

            content += f"### <a id='{anchor_id}'></a>{name}\n\n"
            content += f"[Back to Contents](#contents)\n\n"

            # Add entity description if available
            if entity.get("description"):
                content += f"{entity.get('description')}\n\n"

            # Add top references (limited)
            references = entity.get("references", [])[:5]  # Limit to 5 references
            if references:
                content += "**Key References:**\n\n"
                for ref in references:
                    notebook = ref.get("notebook", "Unknown")
                    page = ref.get("page", "")
                    context = ref.get("context", "")
                    content += f"* **{notebook}** (Page {page})"
                    if context:
                        content += f": {context[:100]}..."
                    content += "\n"

                content += "\n"

        # Add detailed topic sections
        content += "## Topic Details\n\n"
        top_topics = sorted(
            topics, key=lambda t: len(t.get("connections", [])), reverse=True
        )[:20]

        for topic in top_topics:
            name = topic.get("name", "")
            anchor_id = topic_anchors[name]

            content += f"### <a id='{anchor_id}'></a>{name}\n\n"
            content += f"[Back to Contents](#contents)\n\n"

            # Add topic description if available
            if topic.get("description"):
                content += f"{topic.get('description')}\n\n"

            # Add top connections (limited)
            connections = topic.get("connections", [])[:8]  # Limit to 8 connections
            if connections:
                content += "**Key Connected Entities:**\n\n"
                for conn in connections:
                    entity = conn.get("entity", "")
                    entity_type = conn.get("entity_type", "")
                    strength = conn.get("strength", 0)
                    content += f"* {entity} ({entity_type})"
                    if strength:
                        content += f" - relevance: {strength:.2f}"
                    content += "\n"

                content += "\n"

        # Add detailed notebook sections
        content += "## Notebook Details\n\n"
        for notebook in notebooks:
            name = notebook.get("name", "")
            anchor_id = notebook_anchors[name]

            content += f"### <a id='{anchor_id}'></a>{name}\n\n"
            content += f"[Back to Contents](#contents)\n\n"

            # Add notebook summary if available
            if notebook.get("summary"):
                content += f"**Summary:** {notebook.get('summary')}\n\n"

            # Add metadata
            if notebook.get("created_date"):
                content += f"**Created:** {notebook.get('created_date')}\n"
            if notebook.get("page_count"):
                content += f"**Pages:** {notebook.get('page_count')}\n\n"

            # Add top entities (limited)
            entities = notebook.get("entities", [])[:5]  # Limit to 5 entities
            if entities:
                content += "**Key Entities:**\n\n"
                for entity in entities:
                    name = entity.get("name", "")
                    entity_type = entity.get("type", "")
                    count = entity.get("count", 1)
                    content += f"* {name} ({entity_type})"
                    if count > 1:
                        content += f" - {count} mentions"
                    content += "\n"

                content += "\n"

        return content

    def _upload_to_remarkable(self, file_path: str, title: str) -> Tuple[bool, str]:
        """
        Upload an index notebook to reMarkable Cloud.

        Args:
            file_path: Path to the EPUB file
            title: Title for the document

        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if remarkable adapter is available
            if not self.remarkable_adapter:
                return False, "reMarkable adapter not available"

            # Upload file to reMarkable
            success, message = self.remarkable_adapter.upload_file(
                file_path=file_path, title=title
            )

            return success, message

        except Exception as e:
            logger.error(f"Error uploading to reMarkable: {str(e)}")
            return False, str(e)

    def _create_anchor_id(self, text: str) -> str:
        """
        Create a valid HTML anchor ID from text.

        Args:
            text: Text to convert to an anchor ID

        Returns:
            Valid HTML anchor ID
        """
        # Convert to lowercase and replace non-alphanumeric chars with hyphens
        anchor = re.sub(r"[^a-zA-Z0-9]", "-", text.lower())

        # Ensure it starts with a letter (HTML requirement)
        if not anchor[0].isalpha():
            anchor = f"id-{anchor}"

        # Remove consecutive hyphens
        anchor = re.sub(r"-+", "-", anchor)

        # Remove leading/trailing hyphens
        anchor = anchor.strip("-")

        return anchor
