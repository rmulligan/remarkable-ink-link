"""Service for creating and managing knowledge index notebooks."""

import logging
import os
import time
import re
from typing import Dict, List, Any, Optional, Tuple, Set

from inklink.services.epub_generator import EPUBGenerator
from inklink.services.document_service import DocumentService
from inklink.services.remarkable_service import RemarkableService
from inklink.config import CONFIG

logger = logging.getLogger(__name__)


class KnowledgeIndexService:
    """
    Service for creating and managing knowledge index notebooks.

    This service generates structured index notebooks that organize entities and topics
    with references to related content, including notebook names and page numbers.
    """

    def __init__(
        self,
        document_service: Optional[DocumentService] = None,
        remarkable_service: Optional[RemarkableService] = None,
        epub_generator: Optional[EPUBGenerator] = None,
    ):
        """
        Initialize the knowledge index service.

        Args:
            document_service: Service for document creation
            remarkable_service: Service for reMarkable interactions
            epub_generator: Service for generating EPUB documents
        """
        # Initialize services
        self.document_service = document_service or DocumentService()
        self.remarkable_service = remarkable_service or RemarkableService()

        # Configuration
        self.temp_dir = CONFIG.get("TEMP_DIR", "temp")
        self.index_folder_name = CONFIG.get("KNOWLEDGE_INDEX_FOLDER", "Knowledge Index")
        self.auto_update_index = CONFIG.get("AUTO_UPDATE_INDEX", True)
        self.max_references_per_entity = int(
            CONFIG.get("MAX_REFERENCES_PER_ENTITY", 20)
        )
        # Always use EPUB format for indexes - this is inherent, not a config option
        self.use_epub_format = True

        # Initialize EPUB generator
        self.epub_generator = epub_generator or EPUBGenerator(output_dir=self.temp_dir)

        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)

    def create_entity_index(
        self,
        entity_types: Optional[List[str]] = None,
        min_references: int = 1,
        upload_to_remarkable: bool = True,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a comprehensive entity index notebook.

        Args:
            entity_types: Optional list of entity types to include
            min_references: Minimum number of references required to include an entity
            upload_to_remarkable: Whether to upload the index to reMarkable

        Returns:
            Tuple of (success, result dictionary)
        """
        try:
            logger.info("Creating entity index notebook")

            # Mock implementation - in a real system, this would query a knowledge graph
            filtered_entities = self._mock_get_entities(entity_types, min_references)

            # Group entities by type
            entity_groups = self._group_entities_by_type(filtered_entities)

            # Generate markdown content
            markdown_content = self._generate_entity_index_markdown(entity_groups)

            # Create document
            timestamp = int(time.time())
            md_filename = f"entity_index_{timestamp}.md"
            md_path = os.path.join(self.temp_dir, md_filename)

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            # Create documents in different formats
            epub_path = None
            rm_path = None

            # Always create EPUB with hyperlinks for indexes
            # Create entity link map for hyperlinks
            entity_links = self._create_entity_link_map(filtered_entities)

            # Enhance markdown with hyperlinks
            enhanced_markdown = self.epub_generator.enhance_markdown_with_hyperlinks(
                markdown_content=markdown_content, entity_links=entity_links
            )

            # Create EPUB with hyperlinks
            epub_path = self.epub_generator.create_epub_from_markdown(
                markdown_content=enhanced_markdown,
                title=f"Knowledge Entity Index - {time.strftime('%Y-%m-%d')}",
                author="InkLink Knowledge Graph",
                filename=f"entity_index_{timestamp}.epub",
            )

            # Always create reMarkable format as fallback
            rm_path = self.document_service.create_rmdoc_from_content(
                url="",
                qr_path="",
                content={
                    "title": "Knowledge Entity Index",
                    "structured_content": [
                        {"type": "markdown", "content": markdown_content}
                    ],
                },
            )

            # EPUB is the primary format for all indexes, fallback to RM if EPUB creation failed
            primary_path = epub_path if epub_path else rm_path

            if not primary_path:
                return False, {"error": "Failed to create index document"}

            # Upload to reMarkable if requested
            upload_result = {}
            if upload_to_remarkable:
                title = f"Knowledge Entity Index - {time.strftime('%Y-%m-%d')}"
                success, message = self.remarkable_service.upload(primary_path, title)

                upload_result = {"success": success, "message": message, "title": title}

            return True, {
                "entity_count": len(filtered_entities),
                "entity_types": list(entity_groups.keys()),
                "document_path": primary_path,
                "epub_path": epub_path,
                "rm_path": rm_path,
                "upload_result": upload_result,
            }

        except Exception as e:
            logger.error(f"Error creating entity index: {e}")
            return False, {"error": f"Failed to create entity index: {str(e)}"}

    def create_topic_index(
        self,
        top_n_topics: int = 20,
        min_connections: int = 2,
        upload_to_remarkable: bool = True,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a topic index notebook organizing the most important topics.

        Args:
            top_n_topics: Number of top topics to include
            min_connections: Minimum number of connections required to include a topic
            upload_to_remarkable: Whether to upload the index to reMarkable

        Returns:
            Tuple of (success, result dictionary)
        """
        try:
            logger.info("Creating topic index notebook")

            # Mock implementation - in a real system, this would query a knowledge graph
            topics_with_data = self._mock_get_topics(top_n_topics, min_connections)

            # Generate markdown content
            markdown_content = self._generate_topic_index_markdown(topics_with_data)

            # Create document
            timestamp = int(time.time())
            md_filename = f"topic_index_{timestamp}.md"
            md_path = os.path.join(self.temp_dir, md_filename)

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            # Create documents in different formats
            epub_path = None
            rm_path = None

            # Always create EPUB with hyperlinks for indexes
            # Create topic link map for hyperlinks
            topic_links = self._create_topic_link_map(topics_with_data)

            # Enhance markdown with hyperlinks
            enhanced_markdown = self.epub_generator.enhance_markdown_with_hyperlinks(
                markdown_content=markdown_content, entity_links=topic_links
            )

            # Create EPUB with hyperlinks
            epub_path = self.epub_generator.create_epub_from_markdown(
                markdown_content=enhanced_markdown,
                title=f"Knowledge Topic Index - {time.strftime('%Y-%m-%d')}",
                author="InkLink Knowledge Graph",
                filename=f"topic_index_{timestamp}.epub",
            )

            # Always create reMarkable format as fallback
            rm_path = self.document_service.create_rmdoc_from_content(
                url="",
                qr_path="",
                content={
                    "title": "Knowledge Topic Index",
                    "structured_content": [
                        {"type": "markdown", "content": markdown_content}
                    ],
                },
            )

            # EPUB is the primary format for all indexes, fallback to RM if EPUB creation failed
            primary_path = epub_path if epub_path else rm_path

            if not primary_path:
                return False, {"error": "Failed to create topic index document"}

            # Upload to reMarkable if requested
            upload_result = {}
            if upload_to_remarkable:
                title = f"Knowledge Topic Index - {time.strftime('%Y-%m-%d')}"
                success, message = self.remarkable_service.upload(primary_path, title)

                upload_result = {"success": success, "message": message, "title": title}

            return True, {
                "topic_count": len(topics_with_data),
                "document_path": primary_path,
                "epub_path": epub_path,
                "rm_path": rm_path,
                "upload_result": upload_result,
            }

        except Exception as e:
            logger.error(f"Error creating topic index: {e}")
            return False, {"error": f"Failed to create topic index: {str(e)}"}

    def create_notebook_index(
        self, upload_to_remarkable: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create an index of notebooks and their content.

        Args:
            upload_to_remarkable: Whether to upload the index to reMarkable

        Returns:
            Tuple of (success, result dictionary)
        """
        try:
            logger.info("Creating notebook index")

            # Mock implementation - in a real system, this would query a knowledge graph
            notebook_groups = self._mock_get_notebook_groups()

            # Generate markdown content
            markdown_content = self._generate_notebook_index_markdown(notebook_groups)

            # Create document
            timestamp = int(time.time())
            md_filename = f"notebook_index_{timestamp}.md"
            md_path = os.path.join(self.temp_dir, md_filename)

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            # Create documents in different formats
            epub_path = None
            rm_path = None

            # Always create EPUB with hyperlinks for indexes
            # Create notebook link map for hyperlinks
            notebook_links = self._create_notebook_link_map(notebook_groups)

            # Enhance markdown with hyperlinks
            enhanced_markdown = self.epub_generator.enhance_markdown_with_hyperlinks(
                markdown_content=markdown_content, entity_links=notebook_links
            )

            # Create EPUB with hyperlinks
            epub_path = self.epub_generator.create_epub_from_markdown(
                markdown_content=enhanced_markdown,
                title=f"Notebook Content Index - {time.strftime('%Y-%m-%d')}",
                author="InkLink Knowledge Graph",
                filename=f"notebook_index_{timestamp}.epub",
            )

            # Always create reMarkable format as fallback
            rm_path = self.document_service.create_rmdoc_from_content(
                url="",
                qr_path="",
                content={
                    "title": "Notebook Content Index",
                    "structured_content": [
                        {"type": "markdown", "content": markdown_content}
                    ],
                },
            )

            # EPUB is the primary format for all indexes, fallback to RM if EPUB creation failed
            primary_path = epub_path if epub_path else rm_path

            if not primary_path:
                return False, {"error": "Failed to create notebook index document"}

            # Upload to reMarkable if requested
            upload_result = {}
            if upload_to_remarkable:
                title = f"Notebook Content Index - {time.strftime('%Y-%m-%d')}"
                success, message = self.remarkable_service.upload(primary_path, title)

                upload_result = {"success": success, "message": message, "title": title}

            return True, {
                "notebook_count": len(notebook_groups),
                "document_path": primary_path,
                "epub_path": epub_path,
                "rm_path": rm_path,
                "upload_result": upload_result,
            }

        except Exception as e:
            logger.error(f"Error creating notebook index: {e}")
            return False, {"error": f"Failed to create notebook index: {str(e)}"}

    def create_master_index(
        self, upload_to_remarkable: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a master index notebook containing entity, topic, and notebook indices.

        Args:
            upload_to_remarkable: Whether to upload the index to reMarkable

        Returns:
            Tuple of (success, result dictionary)
        """
        try:
            logger.info("Creating master index notebook")

            # Create individual indexes without uploading
            success_entities, entity_result = self.create_entity_index(
                min_references=2, upload_to_remarkable=False
            )

            success_topics, topic_result = self.create_topic_index(
                top_n_topics=15, min_connections=3, upload_to_remarkable=False
            )

            success_notebooks, notebook_result = self.create_notebook_index(
                upload_to_remarkable=False
            )

            # Combine markdown content
            markdown_sections = []

            markdown_sections.append("# Knowledge Graph Master Index\n\n")
            markdown_sections.append(f"*Generated on {time.strftime('%Y-%m-%d')}*\n\n")
            markdown_sections.append(
                "This index provides organized access to your knowledge graph, including entities, topics, and notebooks.\n\n"
            )

            # Add table of contents
            markdown_sections.append("## Table of Contents\n\n")
            markdown_sections.append(
                "1. [Entity Index](#entity-index) - Entities organized by type\n"
            )
            markdown_sections.append(
                "2. [Topic Index](#topic-index) - Important topics with related entities\n"
            )
            markdown_sections.append(
                "3. [Notebook Index](#notebook-index) - Content organized by notebook\n\n"
            )

            # Combine all entity, topic, and notebook links for cross-referencing
            all_links = {}

            # Add entity index if available
            if success_entities:
                markdown_sections.append("## Entity Index\n\n")

                # Extract and include entity sections
                with open(entity_result["rm_path"].replace(".rm", ".md"), "r") as f:
                    entity_content = f.read()

                # Remove the main heading from the entity index
                entity_content = entity_content.replace(
                    "# Knowledge Entity Index\n\n", ""
                )
                markdown_sections.append(entity_content)

                # Get entity links
                if "epub_path" in entity_result and entity_result["epub_path"]:
                    entity_links = self._extract_entity_links_from_epub(
                        entity_result["epub_path"]
                    )
                    all_links.update(entity_links)

            # Add topic index if available
            if success_topics:
                markdown_sections.append("\n## Topic Index\n\n")

                # Extract and include topic sections
                with open(topic_result["rm_path"].replace(".rm", ".md"), "r") as f:
                    topic_content = f.read()

                # Remove the main heading from the topic index
                topic_content = topic_content.replace("# Knowledge Topic Index\n\n", "")
                markdown_sections.append(topic_content)

                # Get topic links
                if "epub_path" in topic_result and topic_result["epub_path"]:
                    topic_links = self._extract_entity_links_from_epub(
                        topic_result["epub_path"]
                    )
                    all_links.update(topic_links)

            # Add notebook index if available
            if success_notebooks:
                markdown_sections.append("\n## Notebook Index\n\n")

                # Extract and include notebook sections
                with open(notebook_result["rm_path"].replace(".rm", ".md"), "r") as f:
                    notebook_content = f.read()

                # Remove the main heading from the notebook index
                notebook_content = notebook_content.replace(
                    "# Notebook Content Index\n\n", ""
                )
                markdown_sections.append(notebook_content)

                # Get notebook links
                if "epub_path" in notebook_result and notebook_result["epub_path"]:
                    notebook_links = self._extract_entity_links_from_epub(
                        notebook_result["epub_path"]
                    )
                    all_links.update(notebook_links)

            # Combine all sections
            markdown_content = "".join(markdown_sections)

            # Create document
            timestamp = int(time.time())
            md_filename = f"master_index_{timestamp}.md"
            md_path = os.path.join(self.temp_dir, md_filename)

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            # Create documents in different formats
            epub_path = None
            rm_path = None

            # Always create EPUB with hyperlinks for indexes
            # Enhance markdown with hyperlinks using all links
            enhanced_markdown = self.epub_generator.enhance_markdown_with_hyperlinks(
                markdown_content=markdown_content, entity_links=all_links
            )

            # Create EPUB with hyperlinks
            epub_path = self.epub_generator.create_epub_from_markdown(
                markdown_content=enhanced_markdown,
                title=f"Knowledge Master Index - {time.strftime('%Y-%m-%d')}",
                author="InkLink Knowledge Graph",
                filename=f"master_index_{timestamp}.epub",
            )

            # Always create reMarkable format as fallback
            rm_path = self.document_service.create_rmdoc_from_content(
                url="",
                qr_path="",
                content={
                    "title": "Knowledge Master Index",
                    "structured_content": [
                        {"type": "markdown", "content": markdown_content}
                    ],
                },
            )

            # EPUB is the primary format for all indexes, fallback to RM if EPUB creation failed
            primary_path = epub_path if epub_path else rm_path

            if not primary_path:
                return False, {"error": "Failed to create master index document"}

            # Upload to reMarkable if requested
            upload_result = {}
            if upload_to_remarkable:
                title = f"Knowledge Master Index - {time.strftime('%Y-%m-%d')}"
                success, message = self.remarkable_service.upload(primary_path, title)

                upload_result = {"success": success, "message": message, "title": title}

            return True, {
                "document_path": primary_path,
                "epub_path": epub_path,
                "rm_path": rm_path,
                "upload_result": upload_result,
                "entity_count": (
                    entity_result.get("entity_count", 0) if success_entities else 0
                ),
                "topic_count": (
                    topic_result.get("topic_count", 0) if success_topics else 0
                ),
                "notebook_count": (
                    notebook_result.get("notebook_count", 0) if success_notebooks else 0
                ),
            }

        except Exception as e:
            logger.error(f"Error creating master index: {e}")
            return False, {"error": f"Failed to create master index: {str(e)}"}

    # Helper methods for entity indexing

    def _create_entity_link_map(self, entities: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Create a mapping of entity names to anchor IDs for hyperlinks.

        Args:
            entities: List of entity dictionaries

        Returns:
            Dictionary mapping entity names to anchor IDs
        """
        entity_links = {}

        for entity in entities:
            entity_name = entity.get("name", "")
            if entity_name:
                # Create a sanitized anchor ID from the entity name
                anchor_id = self._create_anchor_id(entity_name)
                entity_links[entity_name] = anchor_id

                # Also add shorter version without common prefixes/suffixes
                short_name = self._get_short_entity_name(entity_name)
                if short_name and short_name != entity_name:
                    entity_links[short_name] = anchor_id

        return entity_links

    def _create_topic_link_map(self, topics: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Create a mapping of topic names to anchor IDs for hyperlinks.

        Args:
            topics: List of topic dictionaries

        Returns:
            Dictionary mapping topic names to anchor IDs
        """
        topic_links = {}

        for topic in topics:
            topic_name = topic.get("name", "")
            if topic_name:
                # Create a sanitized anchor ID from the topic name
                anchor_id = self._create_anchor_id(topic_name)
                topic_links[topic_name] = anchor_id

        return topic_links

    def _create_notebook_link_map(
        self, notebook_groups: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, str]:
        """
        Create a mapping of notebook names to anchor IDs for hyperlinks.

        Args:
            notebook_groups: Dictionary of notebook groups

        Returns:
            Dictionary mapping notebook names to anchor IDs
        """
        notebook_links = {}

        for notebook_name in notebook_groups:
            if notebook_name:
                # Create a sanitized anchor ID from the notebook name
                anchor_id = self._create_anchor_id(notebook_name)
                notebook_links[notebook_name] = anchor_id

        return notebook_links

    def _create_anchor_id(self, text: str) -> str:
        """
        Create a sanitized anchor ID from text.

        Args:
            text: Input text

        Returns:
            Sanitized anchor ID
        """
        # Remove special characters and convert to lowercase
        anchor_id = re.sub(r"[^\w\s-]", "", text.lower())
        # Replace whitespace with hyphens
        anchor_id = re.sub(r"\s+", "-", anchor_id.strip())
        return anchor_id

    def _get_short_entity_name(self, entity_name: str) -> str:
        """
        Get a shorter version of entity name without common prefixes/suffixes.

        Args:
            entity_name: Full entity name

        Returns:
            Short entity name
        """
        # Remove common prefixes like "The", "A", etc.
        short_name = re.sub(r"^(The|A|An) ", "", entity_name)

        # Remove common suffixes like "Inc.", "Corp.", etc.
        short_name = re.sub(
            r" (Inc\.|Corp\.|LLC|Ltd\.|\& Co\.|\& Sons)$", "", short_name
        )

        return short_name

    def _extract_entity_links_from_epub(self, epub_path: str) -> Dict[str, str]:
        """
        Extract entity links from an EPUB file.

        Args:
            epub_path: Path to the EPUB file

        Returns:
            Dictionary mapping entity names to anchor IDs
        """
        try:
            from ebooklib import epub
            import re

            # Load EPUB
            book = epub.read_epub(epub_path)

            # Extract links from all chapters
            links = {}

            for item in book.get_items_of_type(epub.ITEM_DOCUMENT):
                # Extract links from HTML content
                content = item.get_content().decode("utf-8")

                # Find all <a> tags with href attributes that start with #
                a_tags = re.findall(r'<a href="#([^"]+)"[^>]*>(.*?)</a>', content)

                for anchor, text in a_tags:
                    # Remove any HTML tags from the text
                    clean_text = re.sub(r"<[^>]+>", "", text)
                    links[clean_text] = anchor

            return links

        except Exception as e:
            logger.warning(f"Error extracting links from EPUB: {e}")
            return {}

    def _group_entities_by_type(
        self, entities: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group entities by type.

        Args:
            entities: List of entities to group

        Returns:
            Dictionary mapping entity types to lists of entities
        """
        entity_groups = {}

        for entity in entities:
            entity_type = entity.get("type", "Unknown")

            if entity_type not in entity_groups:
                entity_groups[entity_type] = []

            entity_groups[entity_type].append(entity)

        # Sort entities within each group by name
        for entity_type in entity_groups:
            entity_groups[entity_type].sort(key=lambda e: e.get("name", "").lower())

        return entity_groups

    def _generate_entity_index_markdown(
        self, entity_groups: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """
        Generate markdown content for entity index.

        Args:
            entity_groups: Dictionary mapping entity types to lists of entities

        Returns:
            Markdown content for entity index
        """
        md_lines = []

        # Add title and introduction
        md_lines.append("# Knowledge Entity Index\n")
        md_lines.append(f"*Generated on {time.strftime('%Y-%m-%d')}*\n")
        md_lines.append(
            "This index provides references to entities in your knowledge graph, organized by type.\n"
        )

        # Add table of contents
        md_lines.append("## Contents\n")
        for entity_type in sorted(entity_groups.keys()):
            md_lines.append(
                f"- [{entity_type}s](#{''.join(entity_type.lower().split())}) ({len(entity_groups[entity_type])} entities)\n"
            )

        # Add entities by type
        for entity_type in sorted(entity_groups.keys()):
            md_lines.append(f"\n## {entity_type}s\n")

            for entity in entity_groups[entity_type]:
                # Entity name and basic info
                md_lines.append(f"### {entity.get('name')}\n")

                # Add observations if available
                observations = entity.get("observations", [])
                if observations:
                    md_lines.append("**Description:**\n")
                    for obs in observations[:3]:  # Limit to first 3 observations
                        md_lines.append(f"- {obs}\n")

                    if len(observations) > 3:
                        md_lines.append(f"- *(and {len(observations) - 3} more...)*\n")

                # Add references if available
                references = entity.get("references", [])
                if references:
                    md_lines.append("\n**References:**\n")
                    for ref in references:
                        notebook = ref.get("notebook", "Unknown Notebook")
                        page = ref.get("page", "Unknown")
                        title = ref.get("title", f"Page {page}")

                        md_lines.append(f"- {notebook}, page {page}: *{title}*\n")

                # Add related entities if available
                related_entities = entity.get("related_entities", [])
                if related_entities:
                    md_lines.append("\n**Related Entities:**\n")
                    for rel in related_entities[:7]:  # Limit to 7 related entities
                        rel_name = rel.get("name", "Unknown")
                        rel_type = rel.get("relationship", "related to")

                        # Format relationship phrase based on direction
                        if rel.get("is_source", True):
                            md_lines.append(f"- {rel_type} {rel_name}\n")
                        else:
                            # Reverse the relationship description
                            md_lines.append(f"- {rel_name} {rel_type}\n")

                    if len(related_entities) > 7:
                        md_lines.append(
                            f"- *(and {len(related_entities) - 7} more...)*\n"
                        )

                md_lines.append("\n")

        return "".join(md_lines)

    def _generate_topic_index_markdown(self, topics: List[Dict[str, Any]]) -> str:
        """
        Generate markdown content for topic index.

        Args:
            topics: List of topics with relationship data

        Returns:
            Markdown content for topic index
        """
        md_lines = []

        # Add title and introduction
        md_lines.append("# Knowledge Topic Index\n")
        md_lines.append(f"*Generated on {time.strftime('%Y-%m-%d')}*\n")
        md_lines.append(
            "This index provides information about important topics in your knowledge graph, organized by centrality.\n"
        )

        # Add table of contents
        md_lines.append("## Topics\n")
        for topic in topics:
            md_lines.append(
                f"- [{topic.get('name')}](#{''.join(topic.get('name', '').lower().split())}) ({topic.get('connections', 0)} connections)\n"
            )

        # Add topic sections
        for topic in topics:
            # Topic name and basic info
            md_lines.append(f"\n## {topic.get('name')}\n")
            md_lines.append(f"**Type:** {topic.get('type', 'Unknown')}\n")
            md_lines.append(f"**Connections:** {topic.get('connections', 0)}\n")

            # Add observations if available
            observations = topic.get("observations", [])
            if observations:
                md_lines.append("\n**Description:**\n")
                for obs in observations[:3]:  # Limit to first 3 observations
                    md_lines.append(f"- {obs}\n")

                if len(observations) > 3:
                    md_lines.append(f"- *(and {len(observations) - 3} more...)*\n")

            # Add related entities by relationship type
            relationship_groups = topic.get("relationship_groups", {})
            if relationship_groups:
                md_lines.append("\n**Related Entities:**\n")

                for rel_type, entities in relationship_groups.items():
                    # Skip if no entities for this relationship type
                    if not entities:
                        continue

                    md_lines.append(f"\n*{rel_type}:*\n")

                    # Limit to 5 entities per relationship type
                    for entity in entities[:5]:
                        entity_name = entity.get("name", "Unknown")

                        # Format relationship phrase based on direction
                        if entity.get("is_source", True):
                            md_lines.append(f"- {entity_name}\n")
                        else:
                            md_lines.append(f"- {entity_name}\n")

                    if len(entities) > 5:
                        md_lines.append(f"- *(and {len(entities) - 5} more...)*\n")

            # Add references if available
            references = topic.get("references", [])
            if references:
                md_lines.append("\n**References:**\n")
                for ref in references:
                    notebook = ref.get("notebook", "Unknown Notebook")
                    page = ref.get("page", "Unknown")
                    title = ref.get("title", f"Page {page}")

                    md_lines.append(f"- {notebook}, page {page}: *{title}*\n")

        return "".join(md_lines)

    def _generate_notebook_index_markdown(
        self, notebook_groups: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """
        Generate markdown content for notebook index.

        Args:
            notebook_groups: Dictionary mapping notebook names to lists of pages

        Returns:
            Markdown content for notebook index
        """
        md_lines = []

        # Add title and introduction
        md_lines.append("# Notebook Content Index\n")
        md_lines.append(f"*Generated on {time.strftime('%Y-%m-%d')}*\n")
        md_lines.append(
            "This index provides an overview of your notebooks and their content, including key entities mentioned on each page.\n"
        )

        # Add table of contents
        md_lines.append("## Notebooks\n")
        for notebook_name in sorted(notebook_groups.keys()):
            md_lines.append(
                f"- [{notebook_name}](#{''.join(notebook_name.lower().split())}) ({len(notebook_groups[notebook_name])} pages)\n"
            )

        # Add notebook sections
        for notebook_name in sorted(notebook_groups.keys()):
            md_lines.append(f"\n## {notebook_name}\n")

            # Create table of pages
            md_lines.append("| Page | Title | Key Entities |\n")
            md_lines.append("|------|-------|-------------|\n")

            for page in notebook_groups[notebook_name]:
                page_number = page.get("page_number", "Unknown")
                title = page.get("title", f"Page {page_number}")

                # Format entities (limit to 5 to avoid overly long table cells)
                entities = page.get("entities", [])
                entity_text = ", ".join(entities[:5])
                if len(entities) > 5:
                    entity_text += f", ... ({len(entities) - 5} more)"

                md_lines.append(f"| {page_number} | {title} | {entity_text} |\n")

        return "".join(md_lines)

    # Mock data methods for demonstration

    def _mock_get_entities(
        self, entity_types: Optional[List[str]] = None, min_references: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Mock method to get entities from a knowledge graph.
        In a real implementation, this would query Neo4j or another graph database.

        Args:
            entity_types: Types of entities to include
            min_references: Minimum number of references required

        Returns:
            List of entity dictionaries
        """
        # Sample entity data
        entities = [
            {
                "id": 1,
                "name": "Machine Learning",
                "type": "Concept",
                "observations": [
                    "A field of study that gives computers the ability to learn without being explicitly programmed.",
                    "Often uses statistical techniques to give computers the ability to improve with experience.",
                ],
                "references": [
                    {
                        "notebook": "AI Research",
                        "page": "3",
                        "title": "ML Fundamentals",
                    },
                    {
                        "notebook": "AI Research",
                        "page": "15",
                        "title": "Neural Networks",
                    },
                ],
                "related_entities": [
                    {
                        "name": "Neural Networks",
                        "relationship": "includes",
                        "is_source": True,
                    },
                    {
                        "name": "Data Science",
                        "relationship": "related to",
                        "is_source": True,
                    },
                    {
                        "name": "Artificial Intelligence",
                        "relationship": "is a subset of",
                        "is_source": False,
                    },
                ],
            },
            {
                "id": 2,
                "name": "Neural Networks",
                "type": "Concept",
                "observations": [
                    "Computing systems inspired by biological neural networks that make up animal brains.",
                    "Can learn tasks by considering examples without task-specific programming.",
                ],
                "references": [
                    {
                        "notebook": "AI Research",
                        "page": "15",
                        "title": "Neural Networks",
                    },
                    {
                        "notebook": "Deep Learning Notes",
                        "page": "5",
                        "title": "Architectures",
                    },
                ],
                "related_entities": [
                    {
                        "name": "Deep Learning",
                        "relationship": "used in",
                        "is_source": True,
                    },
                    {
                        "name": "Machine Learning",
                        "relationship": "is part of",
                        "is_source": False,
                    },
                ],
            },
            {
                "id": 3,
                "name": "Python",
                "type": "Technology",
                "observations": [
                    "High-level, interpreted programming language with dynamic semantics.",
                    "Emphasizes code readability and maintainability.",
                ],
                "references": [
                    {"notebook": "Coding Notes", "page": "7", "title": "Python Basics"},
                    {"notebook": "AI Research", "page": "8", "title": "Implementation"},
                ],
                "related_entities": [
                    {
                        "name": "Machine Learning",
                        "relationship": "used for",
                        "is_source": True,
                    },
                    {
                        "name": "TensorFlow",
                        "relationship": "used with",
                        "is_source": True,
                    },
                ],
            },
            {
                "id": 4,
                "name": "TensorFlow",
                "type": "Technology",
                "observations": [
                    "Open-source machine learning framework developed by Google.",
                    "Used for both research and production applications.",
                ],
                "references": [
                    {"notebook": "AI Research", "page": "20", "title": "Frameworks"},
                    {
                        "notebook": "Deep Learning Notes",
                        "page": "12",
                        "title": "TensorFlow Examples",
                    },
                ],
                "related_entities": [
                    {
                        "name": "Python",
                        "relationship": "implemented in",
                        "is_source": False,
                    },
                    {
                        "name": "Neural Networks",
                        "relationship": "implements",
                        "is_source": True,
                    },
                ],
            },
            {
                "id": 5,
                "name": "Geoffrey Hinton",
                "type": "Person",
                "observations": [
                    "British-Canadian cognitive psychologist and computer scientist.",
                    "Known for his work on artificial neural networks and deep learning.",
                ],
                "references": [
                    {
                        "notebook": "AI Research",
                        "page": "25",
                        "title": "Key Researchers",
                    }
                ],
                "related_entities": [
                    {
                        "name": "Neural Networks",
                        "relationship": "researches",
                        "is_source": True,
                    },
                    {
                        "name": "Deep Learning",
                        "relationship": "pioneered",
                        "is_source": True,
                    },
                ],
            },
        ]

        # Filter by entity types if specified
        if entity_types:
            entities = [e for e in entities if e.get("type") in entity_types]

        # Filter by minimum references
        entities = [
            e for e in entities if len(e.get("references", [])) >= min_references
        ]

        return entities

    def _mock_get_topics(
        self, top_n: int = 20, min_connections: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Mock method to get important topics from a knowledge graph.
        In a real implementation, this would query Neo4j or another graph database.

        Args:
            top_n: Number of top topics to include
            min_connections: Minimum number of connections required

        Returns:
            List of topic dictionaries
        """
        # Sample topic data
        topics = [
            {
                "id": 1,
                "name": "Machine Learning",
                "type": "Concept",
                "observations": [
                    "A field of study that gives computers the ability to learn without being explicitly programmed.",
                    "Often uses statistical techniques to give computers the ability to improve with experience.",
                ],
                "connections": 15,
                "references": [
                    {
                        "notebook": "AI Research",
                        "page": "3",
                        "title": "ML Fundamentals",
                    },
                    {
                        "notebook": "AI Research",
                        "page": "15",
                        "title": "Neural Networks",
                    },
                ],
                "relationship_groups": {
                    "INCLUDES": [
                        {"name": "Neural Networks", "is_source": True},
                        {"name": "Deep Learning", "is_source": True},
                        {"name": "Reinforcement Learning", "is_source": True},
                    ],
                    "USED_FOR": [
                        {"name": "Image Recognition", "is_source": True},
                        {"name": "Natural Language Processing", "is_source": True},
                    ],
                    "RELATED_TO": [
                        {"name": "Data Science", "is_source": True},
                        {"name": "Artificial Intelligence", "is_source": True},
                    ],
                },
            },
            {
                "id": 2,
                "name": "Data Science",
                "type": "Concept",
                "observations": [
                    "Interdisciplinary field using scientific methods, processes, and systems to extract knowledge from data.",
                    "Incorporates elements of statistics, machine learning, and database systems.",
                ],
                "connections": 12,
                "references": [
                    {
                        "notebook": "Data Analysis",
                        "page": "5",
                        "title": "Data Science Overview",
                    },
                    {
                        "notebook": "AI Research",
                        "page": "10",
                        "title": "Data-Driven Approaches",
                    },
                ],
                "relationship_groups": {
                    "INCLUDES": [
                        {"name": "Statistics", "is_source": True},
                        {"name": "Data Mining", "is_source": True},
                    ],
                    "USED_FOR": [
                        {"name": "Predictive Analytics", "is_source": True},
                        {"name": "Business Intelligence", "is_source": True},
                    ],
                    "RELATED_TO": [
                        {"name": "Machine Learning", "is_source": True},
                        {"name": "Big Data", "is_source": True},
                    ],
                },
            },
            {
                "id": 3,
                "name": "Artificial Intelligence",
                "type": "Concept",
                "observations": [
                    "Intelligence demonstrated by machines, as opposed to natural intelligence in humans.",
                    "A branch of computer science that aims to create systems capable of performing tasks that typically require human intelligence.",
                ],
                "connections": 10,
                "references": [
                    {
                        "notebook": "AI Research",
                        "page": "1",
                        "title": "AI Introduction",
                    },
                    {
                        "notebook": "Philosophy Notes",
                        "page": "15",
                        "title": "Mind and Machine",
                    },
                ],
                "relationship_groups": {
                    "INCLUDES": [
                        {"name": "Machine Learning", "is_source": True},
                        {"name": "Natural Language Processing", "is_source": True},
                        {"name": "Computer Vision", "is_source": True},
                    ],
                    "APPLICATIONS": [
                        {"name": "Robotics", "is_source": True},
                        {"name": "Expert Systems", "is_source": True},
                    ],
                },
            },
        ]

        # Filter by minimum connections
        topics = [t for t in topics if t.get("connections", 0) >= min_connections]

        # Sort by connections and limit to top_n
        topics.sort(key=lambda x: x.get("connections", 0), reverse=True)
        topics = topics[:top_n]

        return topics

    def _mock_get_notebook_groups(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Mock method to get notebook groups from a knowledge graph.
        In a real implementation, this would query Neo4j or another graph database.

        Returns:
            Dictionary mapping notebook names to lists of pages
        """
        # Sample notebook data
        notebook_groups = {
            "AI Research": [
                {
                    "page_number": "1",
                    "title": "AI Introduction",
                    "entities": [
                        "Artificial Intelligence",
                        "Computer Science",
                        "Turing Test",
                    ],
                },
                {
                    "page_number": "3",
                    "title": "ML Fundamentals",
                    "entities": [
                        "Machine Learning",
                        "Supervised Learning",
                        "Unsupervised Learning",
                    ],
                },
                {
                    "page_number": "8",
                    "title": "Implementation",
                    "entities": ["Python", "Machine Learning", "Libraries"],
                },
                {
                    "page_number": "15",
                    "title": "Neural Networks",
                    "entities": [
                        "Neural Networks",
                        "Machine Learning",
                        "Deep Learning",
                    ],
                },
                {
                    "page_number": "20",
                    "title": "Frameworks",
                    "entities": ["TensorFlow", "PyTorch", "Keras"],
                },
                {
                    "page_number": "25",
                    "title": "Key Researchers",
                    "entities": ["Geoffrey Hinton", "Yann LeCun", "Yoshua Bengio"],
                },
            ],
            "Deep Learning Notes": [
                {
                    "page_number": "5",
                    "title": "Architectures",
                    "entities": ["Neural Networks", "CNN", "RNN", "Transformer"],
                },
                {
                    "page_number": "12",
                    "title": "TensorFlow Examples",
                    "entities": ["TensorFlow", "Code", "Examples"],
                },
                {
                    "page_number": "18",
                    "title": "Training Strategies",
                    "entities": ["Training", "Optimization", "Loss Functions"],
                },
            ],
            "Data Analysis": [
                {
                    "page_number": "5",
                    "title": "Data Science Overview",
                    "entities": ["Data Science", "Statistics", "Programming"],
                },
                {
                    "page_number": "10",
                    "title": "Visualization Techniques",
                    "entities": ["Data Visualization", "Charts", "Matplotlib"],
                },
            ],
            "Philosophy Notes": [
                {
                    "page_number": "15",
                    "title": "Mind and Machine",
                    "entities": [
                        "Artificial Intelligence",
                        "Philosophy of Mind",
                        "Consciousness",
                    ],
                }
            ],
        }

        return notebook_groups
