"""Tests for integration between knowledge graph and reMarkable notebooks."""
import pytest
from unittest.mock import MagicMock

from inklink.services.knowledge_graph_service import KnowledgeGraphService
from inklink.services.handwriting_recognition_service import HandwritingRecognitionService
from inklink.services.round_trip_service import RoundTripService


@pytest.fixture
def mock_handwriting_service():
    """Create a mock handwriting recognition service."""
    service = MagicMock(spec=HandwritingRecognitionService)
    
    # Configure mock to return test stroke data
    service.extract_strokes.return_value = [
        {
            "id": "1",
            "x": [100, 200, 300],
            "y": [100, 150, 100],
            "pressure": [0.5, 0.7, 0.5],
            "timestamp": 1614556800000,
        }
    ]
    
    service.convert_to_iink_format.return_value = {
        "type": "inkData",
        "width": 1872,
        "height": 2404,
        "strokes": [
            {
                "id": "1",
                "x": [100, 200, 300],
                "y": [100, 150, 100],
                "pressure": [0.5, 0.7, 0.5],
                "timestamp": 1614556800000,
            }
        ],
    }
    
    service.recognize_handwriting.return_value = {
        "success": True,
        "content_id": "test_content_id",
        "raw_result": {},
    }
    
    # Return a test note with entities and relationships
    service.export_content.return_value = {
        "success": True,
        "content": {
            "text": "Machine Learning is a field of Artificial Intelligence. "
                   "ML algorithms learn from data and make predictions. "
                   "Neural Networks are a type of ML algorithm inspired by the human brain. "
                   "TensorFlow is a framework developed by Google for implementing Neural Networks."
        },
    }
    
    return service


@pytest.fixture
def mock_knowledge_graph_service():
    """Create a mock knowledge graph service."""
    service = MagicMock(spec=KnowledgeGraphService)
    
    # Mock extract_entities_from_text
    service.extract_entities_from_text.return_value = (True, {
        "count": 5,
        "entities": [
            {"name": "Machine Learning", "type": "Concept", "score": 0.95, "context": "Machine Learning is a field of Artificial Intelligence."},
            {"name": "Artificial Intelligence", "type": "Concept", "score": 0.95, "context": "Machine Learning is a field of Artificial Intelligence."},
            {"name": "ML algorithms", "type": "Concept", "score": 0.85, "context": "ML algorithms learn from data and make predictions."},
            {"name": "Neural Networks", "type": "Concept", "score": 0.95, "context": "Neural Networks are a type of ML algorithm inspired by the human brain."},
            {"name": "TensorFlow", "type": "Product", "score": 0.95, "context": "TensorFlow is a framework developed by Google for implementing Neural Networks."}
        ]
    })
    
    # Mock extract_relationships_from_text
    service.extract_relationships_from_text.return_value = (True, {
        "count": 3,
        "relationships": [
            {"from": "Machine Learning", "to": "Artificial Intelligence", "type": "PART_OF", "score": 0.9},
            {"from": "Neural Networks", "to": "Machine Learning", "type": "INSTANCE_OF", "score": 0.9},
            {"from": "TensorFlow", "to": "Neural Networks", "type": "USED_FOR", "score": 0.85}
        ]
    })
    
    # Mock create_entity
    service.create_entity.return_value = (True, {"id": "123", "name": "Machine Learning", "type": "Concept"})
    
    # Mock create_relationship
    service.create_relationship.return_value = (True, {"id": "456", "from": "Machine Learning", "to": "Artificial Intelligence", "type": "PART_OF"})
    
    # Mock create_semantic_links
    service.create_semantic_links.return_value = (True, {
        "entity": "Machine Learning",
        "similar_entities": [
            {"entity": "Deep Learning", "type": "Concept", "similarity": 0.87},
            {"entity": "Data Science", "type": "Concept", "similarity": 0.75}
        ],
        "links_created": 2
    })
    
    # Mock find_semantically_similar_text
    service.find_semantically_similar_text.return_value = (True, {
        "query": "Neural Network architectures for image recognition",
        "results": [
            {"entity": "Convolutional Neural Networks", "type": "Concept", "similarity": 0.91},
            {"entity": "Computer Vision", "type": "Concept", "similarity": 0.85},
            {"entity": "Image Classification", "type": "Concept", "similarity": 0.82}
        ],
        "count": 3
    })
    
    return service


@pytest.fixture
def round_trip_service(mock_handwriting_service, mock_knowledge_graph_service):
    """Create a RoundTripService with mock dependencies."""
    document_service = MagicMock()
    remarkable_service = MagicMock()
    
    return RoundTripService(
        handwriting_service=mock_handwriting_service,
        document_service=document_service,
        remarkable_service=remarkable_service,
    )


def test_extract_entities_from_remarkable_notebook(round_trip_service, mock_handwriting_service, mock_knowledge_graph_service):
    """Test extracting entities from a reMarkable notebook."""
    # Create a test handwritten note path
    rm_file_path = "/path/to/test_handwritten_note.rm"
    
    # Create the knowledge graph notebook extractor function
    def extract_knowledge_from_notebook(rm_file_path, knowledge_graph_service):
        # Use handwriting recognition to get text from the notebook
        strokes = round_trip_service.handwriting_service.extract_strokes(rm_file_path)
        if not strokes:
            return False, {"error": "No strokes found in file"}
            
        iink_data = round_trip_service.handwriting_service.convert_to_iink_format(strokes)
        recognition_result = round_trip_service.handwriting_service.recognize_handwriting(iink_data)
        
        if not recognition_result.get("success", False):
            return False, {"error": f"Recognition failed: {recognition_result.get('error')}"}
            
        content_id = recognition_result.get("content_id")
        export_result = round_trip_service.handwriting_service.export_content(content_id, "text")
        
        if not export_result.get("success", False):
            return False, {"error": f"Export failed: {export_result.get('error')}"}
            
        recognized_text = export_result.get("content", {}).get("text", "").strip()
        if not recognized_text:
            return False, {"error": "No text recognized"}
            
        # Extract entities from the recognized text
        success, entities_result = knowledge_graph_service.extract_entities_from_text(recognized_text)
        if not success:
            return False, {"error": f"Entity extraction failed: {entities_result.get('error')}"}
            
        # Create entities in the knowledge graph
        created_entities = []
        for entity in entities_result.get("entities", []):
            entity_name = entity.get("name")
            entity_type = entity.get("type")
            # Only create entities with high confidence
            if entity.get("score", 0) > 0.7:
                success, entity_result = knowledge_graph_service.create_entity(
                    name=entity_name,
                    entity_type=entity_type,
                    observations=[entity.get("context", "")]
                )
                if success:
                    created_entities.append(entity_result)
                    
        # Extract relationships from the recognized text
        created_relationships = []
        for entity in created_entities:
            entity_name = entity.get("name")
            success, rel_result = knowledge_graph_service.extract_relationships_from_text(
                text=recognized_text,
                from_entity=entity_name
            )
            
            if success:
                for relationship in rel_result.get("relationships", []):
                    # Only create relationships with high confidence
                    if relationship.get("score", 0) > 0.7:
                        success, rel_created = knowledge_graph_service.create_relationship(
                            from_entity=relationship.get("from"),
                            to_entity=relationship.get("to"),
                            relationship_type=relationship.get("type")
                        )
                        if success:
                            created_relationships.append(rel_created)
                            
        # Create semantic links for the entities
        semantic_links = []
        for entity in created_entities:
            entity_name = entity.get("name")
            success, links_result = knowledge_graph_service.create_semantic_links(
                entity_name=entity_name,
                min_similarity=0.7,
                max_links=5
            )
            if success:
                semantic_links.append(links_result)
                
        return True, {
            "recognized_text": recognized_text,
            "entities": created_entities,
            "relationships": created_relationships,
            "semantic_links": semantic_links
        }
    
    # Run the test
    success, result = extract_knowledge_from_notebook(rm_file_path, mock_knowledge_graph_service)
    
    # Verify success
    assert success is True
    
    # Verify the services were called correctly
    mock_handwriting_service.extract_strokes.assert_called_once_with(rm_file_path)
    mock_handwriting_service.convert_to_iink_format.assert_called_once()
    mock_handwriting_service.recognize_handwriting.assert_called_once()
    mock_handwriting_service.export_content.assert_called_once_with("test_content_id", "text")
    
    # Verify entity extraction was called
    mock_knowledge_graph_service.extract_entities_from_text.assert_called_once()
    
    # Verify relationship extraction was called
    assert mock_knowledge_graph_service.extract_relationships_from_text.call_count > 0
    
    # Verify entity creation was called
    assert mock_knowledge_graph_service.create_entity.call_count > 0
    
    # Verify relationship creation was called
    assert mock_knowledge_graph_service.create_relationship.call_count > 0
    
    # Verify semantic links were created
    assert mock_knowledge_graph_service.create_semantic_links.call_count > 0
    
    # Verify the result structure
    assert "recognized_text" in result
    assert "entities" in result
    assert "relationships" in result
    assert "semantic_links" in result
    assert len(result["entities"]) > 0
    assert len(result["relationships"]) > 0
    assert len(result["semantic_links"]) > 0


def test_semantic_search_from_handwritten_query(round_trip_service, mock_handwriting_service, mock_knowledge_graph_service):
    """Test semantic search using a handwritten query."""
    # Create a test handwritten query path
    rm_file_path = "/path/to/test_handwritten_query.rm"
    
    # Define the semantic search function
    def search_knowledge_graph_from_handwriting(rm_file_path, knowledge_graph_service):
        # Use handwriting recognition to get text from the notebook
        strokes = round_trip_service.handwriting_service.extract_strokes(rm_file_path)
        if not strokes:
            return False, {"error": "No strokes found in file"}
            
        iink_data = round_trip_service.handwriting_service.convert_to_iink_format(strokes)
        recognition_result = round_trip_service.handwriting_service.recognize_handwriting(iink_data)
        
        if not recognition_result.get("success", False):
            return False, {"error": f"Recognition failed: {recognition_result.get('error')}"}
            
        content_id = recognition_result.get("content_id")
        export_result = round_trip_service.handwriting_service.export_content(content_id, "text")
        
        if not export_result.get("success", False):
            return False, {"error": f"Export failed: {export_result.get('error')}"}
            
        query_text = export_result.get("content", {}).get("text", "").strip()
        if not query_text:
            return False, {"error": "No text recognized in query"}
            
        # Perform semantic search using the query text
        success, search_result = knowledge_graph_service.find_semantically_similar_text(
            text=query_text,
            min_similarity=0.6,
            max_results=10
        )
        
        if not success:
            return False, {"error": f"Semantic search failed: {search_result.get('error')}"}
            
        return True, {
            "query": query_text,
            "search_results": search_result.get("results", []),
            "result_count": search_result.get("count", 0)
        }
    
    # Run the test
    success, result = search_knowledge_graph_from_handwriting(rm_file_path, mock_knowledge_graph_service)
    
    # Verify success
    assert success is True
    
    # Verify the services were called correctly
    mock_handwriting_service.extract_strokes.assert_called_once_with(rm_file_path)
    mock_handwriting_service.convert_to_iink_format.assert_called_once()
    mock_handwriting_service.recognize_handwriting.assert_called_once()
    mock_handwriting_service.export_content.assert_called_once_with("test_content_id", "text")
    
    # Verify semantic search was called
    mock_knowledge_graph_service.find_semantically_similar_text.assert_called_once()
    
    # Verify the result structure
    assert "query" in result
    assert "search_results" in result
    assert "result_count" in result
    assert len(result["search_results"]) > 0
    assert result["search_results"][0]["entity"] == "Convolutional Neural Networks"
    assert result["search_results"][0]["similarity"] > 0.9