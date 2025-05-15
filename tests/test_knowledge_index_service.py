"""Tests for the Knowledge Index Service."""
import tempfile
from unittest import mock

import pytest

from inklink.services.knowledge_index_service import KnowledgeIndexService
from inklink.services.epub_generator import EPUBGenerator
from inklink.services.knowledge_graph_service import KnowledgeGraphService
from inklink.adapters.remarkable_adapter import RemarkableAdapter


@pytest.fixture
def mock_kg_service():
    """Mock Knowledge Graph Service."""
    mock_service = mock.MagicMock(spec=KnowledgeGraphService)

    # Mock entity data
    mock_service.get_entities.return_value = [
        {
            "name": "Entity1",
            "type": "Person",
            "references": [
                {
                    "notebook": "Notebook1",
                    "page": "1",
                    "context": "Entity1 was mentioned here",
                },
                {"notebook": "Notebook2", "page": "5", "context": "More about Entity1"},
            ],
        },
        {
            "name": "Entity2",
            "type": "Concept",
            "references": [
                {"notebook": "Notebook1", "page": "2", "context": "Entity2 definition"}
            ],
        },
    ]

    # Mock topic data
    mock_service.get_topics.return_value = [
        {
            "name": "Topic1",
            "connections": [
                {"entity": "Entity1", "entity_type": "Person", "strength": 0.8},
                {"entity": "Entity2", "entity_type": "Concept", "strength": 0.6},
            ],
        }
    ]

    # Mock notebook data
    mock_service.get_notebooks.return_value = [
        {
            "name": "Notebook1",
            "page_count": 10,
            "entities": [
                {"name": "Entity1", "type": "Person", "count": 2},
                {"name": "Entity2", "type": "Concept", "count": 1},
            ],
            "topics": [{"name": "Topic1", "relevance": 0.9}],
        }
    ]

    return mock_service


@pytest.fixture
def mock_epub_generator():
    """Mock EPUB Generator."""
    mock_generator = mock.MagicMock(spec=EPUBGenerator)

    # Mock successful EPUB creation
    mock_generator.create_epub_from_markdown.return_value = (
        True,
        {"path": "/tmp/test.epub", "title": "Test Index", "size": 12345},
    )

    # Mock markdown enhancement
    mock_generator.enhance_markdown_with_hyperlinks.return_value = "Enhanced markdown"

    return mock_generator


@pytest.fixture
def mock_remarkable_adapter():
    """Mock reMarkable Adapter."""
    mock_adapter = mock.MagicMock(spec=RemarkableAdapter)

    # Mock successful upload
    mock_adapter.upload_file.return_value = (
        True,
        "Successfully uploaded to reMarkable",
    )

    return mock_adapter


@pytest.fixture
def knowledge_index_service(
    mock_kg_service, mock_epub_generator, mock_remarkable_adapter
):
    """Create a KnowledgeIndexService with mocked dependencies."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        service = KnowledgeIndexService(
            knowledge_graph_service=mock_kg_service,
            epub_generator=mock_epub_generator,
            remarkable_adapter=mock_remarkable_adapter,
            output_dir=tmp_dir,
        )
        yield service


def test_create_entity_index(
    knowledge_index_service, mock_kg_service, mock_epub_generator
):
    """Test creating an entity index."""
    # Call service
    success, result = knowledge_index_service.create_entity_index(
        entity_types=["Person", "Concept"], min_references=1, upload_to_remarkable=True
    )

    # Check success
    assert success is True

    # Verify interactions
    mock_kg_service.get_entities.assert_called_once_with(types=["Person", "Concept"])
    mock_epub_generator.create_epub_from_markdown.assert_called_once()

    # Verify result fields
    assert "entity_count" in result
    assert "entity_types" in result
    assert "path" in result
    assert "upload_result" in result


def test_create_topic_index(
    knowledge_index_service, mock_kg_service, mock_epub_generator
):
    """Test creating a topic index."""
    # Call service
    success, result = knowledge_index_service.create_topic_index(
        top_n_topics=20, min_connections=1, upload_to_remarkable=True
    )

    # Check success
    assert success is True

    # Verify interactions
    mock_kg_service.get_topics.assert_called_once_with(limit=20, min_connections=1)
    mock_epub_generator.create_epub_from_markdown.assert_called_once()

    # Verify result fields
    assert "topic_count" in result
    assert "path" in result
    assert "upload_result" in result


def test_create_notebook_index(
    knowledge_index_service, mock_kg_service, mock_epub_generator
):
    """Test creating a notebook index."""
    # Call service
    success, result = knowledge_index_service.create_notebook_index(
        upload_to_remarkable=True
    )

    # Check success
    assert success is True

    # Verify interactions
    mock_kg_service.get_notebooks.assert_called_once()
    mock_epub_generator.create_epub_from_markdown.assert_called_once()

    # Verify result fields
    assert "notebook_count" in result
    assert "path" in result
    assert "upload_result" in result


def test_create_master_index(
    knowledge_index_service, mock_kg_service, mock_epub_generator
):
    """Test creating a master index."""
    # Call service
    success, result = knowledge_index_service.create_master_index(
        upload_to_remarkable=True
    )

    # Check success
    assert success is True

    # Verify interactions
    mock_kg_service.get_entities.assert_called_once()
    mock_kg_service.get_topics.assert_called_once()
    mock_kg_service.get_notebooks.assert_called_once()
    mock_epub_generator.create_epub_from_markdown.assert_called_once()

    # Verify result fields
    assert "entity_count" in result
    assert "topic_count" in result
    assert "notebook_count" in result
    assert "path" in result
    assert "upload_result" in result


def test_epub_format_is_inherent(
    mock_kg_service, mock_epub_generator, mock_remarkable_adapter
):
    """Test that EPUB format is inherent, not a config option."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create service
        service = KnowledgeIndexService(
            knowledge_graph_service=mock_kg_service,
            epub_generator=mock_epub_generator,
            remarkable_adapter=mock_remarkable_adapter,
            output_dir=tmp_dir,
        )

        # Verify that use_epub_format is True and can't be changed
        assert service.use_epub_format is True

        # Attempt to change the attribute (should have no effect in real usage)
        service.use_epub_format = False

        # Verify it remains True (this is a contrived test, as in real code we'd never try to modify this)
        assert service.use_epub_format is True
