"""Integration service for knowledge graph and reMarkable notebooks."""
import logging
from typing import Dict, List, Any, Optional, Tuple

from inklink.services.handwriting_recognition_service import HandwritingRecognitionService
from inklink.services.knowledge_graph_service import KnowledgeGraphService
from inklink.services.remarkable_service import RemarkableService
from inklink.config import CONFIG

logger = logging.getLogger(__name__)


class KnowledgeGraphIntegrationService:
    """
    Service for integrating knowledge graph capabilities with reMarkable notebooks.

    This service combines handwriting recognition with knowledge graph operations
    to extract structured knowledge from handwritten notes, create semantic links,
    and enable semantic search of knowledge using handwritten queries.
    """

    def __init__(
        self,
        handwriting_service: Optional[HandwritingRecognitionService] = None,
        knowledge_graph_service: Optional[KnowledgeGraphService] = None,
        remarkable_service: Optional[RemarkableService] = None,
    ):
        """
        Initialize the integration service.

        Args:
            handwriting_service: Service for handwriting recognition
            knowledge_graph_service: Service for knowledge graph operations
            remarkable_service: Service for reMarkable interactions
        """
        # Initialize default services if not provided
        self.handwriting_service = handwriting_service or HandwritingRecognitionService()
        self.knowledge_graph_service = knowledge_graph_service or KnowledgeGraphService()
        self.remarkable_service = remarkable_service or RemarkableService()

        # Configuration
        self.min_entity_confidence = float(CONFIG.get("KG_MIN_ENTITY_CONFIDENCE", "0.7"))
        self.min_relation_confidence = float(CONFIG.get("KG_MIN_RELATION_CONFIDENCE", "0.7"))
        self.min_semantic_similarity = float(CONFIG.get("KG_MIN_SEMANTIC_SIMILARITY", "0.6"))
        self.max_semantic_links = int(CONFIG.get("KG_MAX_SEMANTIC_LINKS", "5"))

    def extract_knowledge_from_notebook(
        self, rm_file_path: str, entity_types: Optional[List[str]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Extract knowledge graph entities and relationships from a reMarkable notebook.

        Args:
            rm_file_path: Path to the .rm file with handwritten notes
            entity_types: Optional list of entity types to extract

        Returns:
            Tuple of (success, result dictionary)
        """
        try:
            logger.info(f"Extracting knowledge from notebook: {rm_file_path}")

            # Step 1: Extract and recognize text from the notebook
            recognized_text = self._recognize_text_from_file(rm_file_path)
            if not recognized_text:
                return False, {"error": "Failed to recognize text from notebook"}

            # Step 2: Extract entities from the recognized text
            success, entities_result = self.knowledge_graph_service.extract_entities_from_text(
                text=recognized_text,
                entity_types=entity_types
            )

            if not success:
                return False, {
                    "error": f"Entity extraction failed: {entities_result.get('error')}",
                    "recognized_text": recognized_text
                }

            # Step 3: Create entities in the knowledge graph
            created_entities = []
            for entity in entities_result.get("entities", []):
                # Only create entities with confidence above threshold
                if entity.get("score", 0) >= self.min_entity_confidence:
                    success, entity_result = self.knowledge_graph_service.create_entity(
                        name=entity.get("name"),
                        entity_type=entity.get("type", "Concept"),
                        observations=[entity.get("context", "Extracted from handwritten notes")]
                    )
                    if success:
                        created_entities.append(entity_result)

            # Step 4: Extract and create relationships between entities
            created_relationships = []
            for entity in created_entities:
                entity_name = entity.get("name")
                success, rel_result = self.knowledge_graph_service.extract_relationships_from_text(
                    text=recognized_text,
                    from_entity=entity_name
                )

                if success:
                    for relationship in rel_result.get("relationships", []):
                        # Only create relationships with confidence above threshold
                        if relationship.get("score", 0) >= self.min_relation_confidence:
                            success, rel_created = self.knowledge_graph_service.create_relationship(
                                from_entity=relationship.get("from"),
                                to_entity=relationship.get("to"),
                                relationship_type=relationship.get("type", "RELATED_TO")
                            )
                            if success:
                                created_relationships.append(rel_created)

            # Step 5: Create semantic links for the entities
            semantic_links = []
            for entity in created_entities:
                entity_name = entity.get("name")
                success, links_result = self.knowledge_graph_service.create_semantic_links(
                    entity_name=entity_name,
                    min_similarity=self.min_semantic_similarity,
                    max_links=self.max_semantic_links,
                    entity_types=entity_types
                )
                if success:
                    semantic_links.append(links_result)

            return True, {
                "recognized_text": recognized_text,
                "extracted_entities": entities_result.get("entities", []),
                "created_entities": created_entities,
                "created_relationships": created_relationships,
                "semantic_links": semantic_links
            }

        except Exception as e:
            logger.error(f"Error extracting knowledge from notebook: {e}")
            return False, {"error": f"Knowledge extraction failed: {str(e)}"}

    def semantic_search_from_handwritten_query(
        self,
        rm_file_path: str,
        min_similarity: float = 0.6,
        max_results: int = 10,
        entity_types: Optional[List[str]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Perform semantic search using a handwritten query from a reMarkable notebook.

        Args:
            rm_file_path: Path to the .rm file with handwritten query
            min_similarity: Minimum similarity threshold (0-1)
            max_results: Maximum number of results to return
            entity_types: Optional list of entity types to filter by

        Returns:
            Tuple of (success, result dictionary)
        """
        try:
            logger.info(f"Performing semantic search from handwritten query: {rm_file_path}")

            # Step 1: Extract and recognize text from the query
            query_text = self._recognize_text_from_file(rm_file_path)
            if not query_text:
                return False, {"error": "Failed to recognize text from handwritten query"}

            # Step 2: Perform semantic search using the query text
            success, search_result = self.knowledge_graph_service.find_semantically_similar_text(
                text=query_text,
                min_similarity=min_similarity,
                max_results=max_results,
                entity_types=entity_types
            )

            if not success:
                return False, {
                    "error": f"Semantic search failed: {search_result.get('error')}",
                    "query": query_text
                }

            return True, {
                "query": query_text,
                "search_results": search_result.get("results", []),
                "result_count": search_result.get("count", 0)
            }

        except Exception as e:
            logger.error(f"Error performing semantic search from handwritten query: {e}")
            return False, {"error": f"Semantic search failed: {str(e)}"}

    def _recognize_text_from_file(self, rm_file_path: str) -> Optional[str]:
        """
        Helper method to recognize text from a reMarkable file.

        Args:
            rm_file_path: Path to the .rm file

        Returns:
            Recognized text or None if recognition failed
        """
        try:
            # Extract strokes from the file
            strokes = self.handwriting_service.extract_strokes(rm_file_path)
            if not strokes:
                logger.warning(f"No strokes found in file: {rm_file_path}")
                return None

            # Convert strokes to iink format
            iink_data = self.handwriting_service.convert_to_iink_format(strokes)

            # Recognize handwriting
            recognition_result = self.handwriting_service.recognize_handwriting(iink_data)
            if not recognition_result.get("success", False):
                logger.warning(f"Recognition failed: {recognition_result.get('error')}")
                return None

            # Export as text
            content_id = recognition_result.get("content_id")
            export_result = self.handwriting_service.export_content(content_id, "text")
            if not export_result.get("success", False):
                logger.warning(f"Export failed: {export_result.get('error')}")
                return None

            # Extract the recognized text
            recognized_text = export_result.get("content", {}).get("text", "").strip()
            return recognized_text

        except Exception as e:
            logger.error(f"Error recognizing text from file: {e}")
            return None

    def augment_notebook_with_knowledge(
        self, 
        rm_file_path: str, 
        include_related: bool = True,
        include_semantic: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Augment a reMarkable notebook with knowledge graph information.

        This extracts entities from the notebook, then finds related information
        in the knowledge graph to enrich the notebook with additional context.

        Args:
            rm_file_path: Path to the .rm file with handwritten notes
            include_related: Whether to include related entities via relationships
            include_semantic: Whether to include semantically similar entities

        Returns:
            Tuple of (success, result dictionary)
        """
        try:
            logger.info(f"Augmenting notebook with knowledge: {rm_file_path}")

            # Step 1: Extract and recognize text from the notebook
            recognized_text = self._recognize_text_from_file(rm_file_path)
            if not recognized_text:
                return False, {"error": "Failed to recognize text from notebook"}

            # Step 2: Extract entities from the recognized text
            success, entities_result = self.knowledge_graph_service.extract_entities_from_text(
                text=recognized_text
            )

            if not success:
                return False, {
                    "error": f"Entity extraction failed: {entities_result.get('error')}",
                    "recognized_text": recognized_text
                }

            # Step 3: Gather knowledge for each entity
            enriched_entities = []
            for entity in entities_result.get("entities", []):
                if entity.get("score", 0) >= self.min_entity_confidence:
                    entity_name = entity.get("name")
                    entity_info = {"name": entity_name, "type": entity.get("type", "Concept")}

                    # Check if entity exists in knowledge graph
                    success, entity_result = self.knowledge_graph_service.get_entity(entity_name)

                    if success:
                        # Entity exists, gather related information
                        entity_info["exists"] = True
                        entity_info["observations"] = entity_result.get("properties", {}).get("observations", [])

                        # Get related entities through relationships
                        if include_related:
                            success, related_result = self.knowledge_graph_service.get_entity_relationships(
                                entity_name=entity_name
                            )
                            if success:
                                entity_info["related_entities"] = related_result.get("related_entities", [])

                        # Get semantically similar entities
                        if include_semantic:
                            success, semantic_result = self.knowledge_graph_service.create_semantic_links(
                                entity_name=entity_name,
                                min_similarity=self.min_semantic_similarity,
                                max_links=5
                            )
                            if success:
                                entity_info["similar_entities"] = semantic_result.get("similar_entities", [])
                    else:
                        # Entity doesn't exist yet
                        entity_info["exists"] = False

                    enriched_entities.append(entity_info)

            # Step 4: Structure the augmented content
            augmented_content = {
                "original_text": recognized_text,
                "entities": enriched_entities,
                "summary": f"Found {len(enriched_entities)} key concepts in your notes."
            }

            return True, augmented_content

        except Exception as e:
            logger.error(f"Error augmenting notebook with knowledge: {e}")
            return False, {"error": f"Notebook augmentation failed: {str(e)}"}