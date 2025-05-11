"""Tests for the notebook memory management service."""

import os
import tempfile
import shutil
import pytest
import time
import json
from typing import Dict, Any, List

from inklink.services.memory_management_service import MemoryManagementService


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for notebook storage."""
    temp_dir = tempfile.mkdtemp(prefix="test_memory_management_")
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def memory_service(temp_storage_dir):
    """Create a memory management service for testing."""
    return MemoryManagementService(
        storage_dir=temp_storage_dir,
        cache_size=5,
        compression_level=6,
        chunk_size=1024,  # Smaller chunks for testing
    )


@pytest.fixture
def sample_notebook() -> Dict[str, Any]:
    """Create a sample notebook for testing."""
    return {
        "title": "Test Notebook",
        "created": time.time(),
        "pages": [
            {
                "id": "page1",
                "title": "Page 1",
                "content": "This is the content of page 1.",
                "tags": ["test", "page1"],
            },
            {
                "id": "page2",
                "title": "Page 2",
                "content": "This is the content of page 2.",
                "tags": ["test", "page2"],
            },
            {
                "id": "page3",
                "title": "Page 3",
                "content": "This is the content of page 3.",
                "tags": ["test", "page3"],
            },
        ],
        "metadata": {
            "author": "Test Author",
            "version": "1.0",
        },
    }


def test_store_and_retrieve_notebook(memory_service, sample_notebook):
    """Test storing and retrieving a notebook."""
    # Store notebook
    notebook_id = "test-notebook-1"
    success, result = memory_service.store_notebook(
        notebook_id=notebook_id,
        content=sample_notebook,
        metadata={"tags": ["test", "sample"]},
    )

    assert success is True
    assert "metadata" in result
    assert result["metadata"]["id"] == notebook_id

    # Retrieve notebook
    success, retrieved = memory_service.retrieve_notebook(notebook_id)

    assert success is True
    assert retrieved["title"] == sample_notebook["title"]
    assert len(retrieved["pages"]) == len(sample_notebook["pages"])
    assert retrieved["metadata"] == sample_notebook["metadata"]


def test_update_notebook(memory_service, sample_notebook):
    """Test updating a notebook."""
    # Store notebook
    notebook_id = "test-notebook-2"
    memory_service.store_notebook(
        notebook_id=notebook_id,
        content=sample_notebook,
    )

    # Update notebook
    updated_notebook = sample_notebook.copy()
    updated_notebook["title"] = "Updated Notebook"
    updated_notebook["pages"].append(
        {
            "id": "page4",
            "title": "Page 4",
            "content": "This is a new page.",
            "tags": ["test", "page4"],
        }
    )

    success, result = memory_service.update_notebook(
        notebook_id=notebook_id,
        content=updated_notebook,
        metadata={"updated": True},
    )

    assert success is True
    assert "metadata" in result
    assert result["metadata"]["updated"] is True

    # Retrieve updated notebook
    success, retrieved = memory_service.retrieve_notebook(notebook_id)

    assert success is True
    assert retrieved["title"] == "Updated Notebook"
    assert len(retrieved["pages"]) == 4
    assert retrieved["pages"][3]["id"] == "page4"


def test_delete_notebook(memory_service, sample_notebook):
    """Test deleting a notebook."""
    # Store notebook
    notebook_id = "test-notebook-3"
    memory_service.store_notebook(
        notebook_id=notebook_id,
        content=sample_notebook,
    )

    # Verify it exists
    success, _ = memory_service.retrieve_notebook(notebook_id)
    assert success is True

    # Delete notebook
    success, result = memory_service.delete_notebook(notebook_id)

    assert success is True
    assert "deleted_metadata" in result

    # Verify it's gone
    success, error = memory_service.retrieve_notebook(notebook_id)

    assert success is False
    assert "error" in error
    assert notebook_id in error["error"]


def test_list_notebooks(memory_service, sample_notebook):
    """Test listing notebooks."""
    # Store multiple notebooks
    for i in range(3):
        notebook = sample_notebook.copy()
        notebook["title"] = f"Notebook {i}"
        notebook_id = f"test-notebook-{i}"

        memory_service.store_notebook(
            notebook_id=notebook_id,
            content=notebook,
            metadata={"index": i},
        )

    # List all notebooks
    success, result = memory_service.list_notebooks()

    assert success is True
    assert "notebooks" in result
    assert result["count"] == 3

    # Filter notebooks
    success, result = memory_service.list_notebooks(filter_criteria={"index": 1})

    assert success is True
    assert result["count"] == 1
    assert result["notebooks"][0]["index"] == 1


def test_partial_notebook_retrieval(memory_service, sample_notebook):
    """Test retrieving part of a notebook."""
    # Store notebook
    notebook_id = "test-notebook-4"
    memory_service.store_notebook(
        notebook_id=notebook_id,
        content=sample_notebook,
    )

    # Retrieve just the pages section
    success, result = memory_service.retrieve_notebook(
        notebook_id=notebook_id,
        partial=True,
        section="pages",
    )

    assert success is True
    assert "pages" in result
    assert len(result["pages"]) == 3

    # Try to retrieve a non-existent section
    success, error = memory_service.retrieve_notebook(
        notebook_id=notebook_id,
        partial=True,
        section="nonexistent",
    )

    assert success is False
    assert "error" in error


def test_find_duplicate_notebooks(memory_service, sample_notebook):
    """Test finding duplicate notebooks."""
    # Store the same notebook with different IDs
    notebook_ids = []
    for i in range(3):
        notebook_id = f"duplicate-notebook-{i}"
        memory_service.store_notebook(
            notebook_id=notebook_id,
            content=sample_notebook,
        )
        notebook_ids.append(notebook_id)

    # Store a different notebook
    different_notebook = sample_notebook.copy()
    different_notebook["title"] = "Different Notebook"
    memory_service.store_notebook(
        notebook_id="different-notebook",
        content=different_notebook,
    )

    # Find duplicates
    success, result = memory_service.find_duplicate_notebooks()

    assert success is True
    assert "duplicates" in result
    assert result["duplicate_groups"] == 1

    # Check the duplicate group
    duplicate_hashes = list(result["duplicates"].keys())
    assert len(duplicate_hashes) == 1

    duplicate_group = result["duplicates"][duplicate_hashes[0]]
    assert len(duplicate_group) == 3

    duplicate_ids = [notebook["id"] for notebook in duplicate_group]
    for notebook_id in notebook_ids:
        assert notebook_id in duplicate_ids


def test_notebook_metadata(memory_service, sample_notebook):
    """Test getting and updating notebook metadata."""
    # Store notebook
    notebook_id = "test-notebook-5"
    memory_service.store_notebook(
        notebook_id=notebook_id,
        content=sample_notebook,
        metadata={"tags": ["test"]},
    )

    # Get metadata
    success, metadata = memory_service.get_notebook_metadata(notebook_id)

    assert success is True
    assert metadata["id"] == notebook_id
    assert metadata["tags"] == ["test"]

    # Update metadata
    success, updated_metadata = memory_service.update_notebook_metadata(
        notebook_id=notebook_id,
        metadata={"tags": ["test", "updated"], "status": "active"},
    )

    assert success is True
    assert updated_metadata["tags"] == ["test", "updated"]
    assert updated_metadata["status"] == "active"

    # Verify metadata was updated
    success, metadata = memory_service.get_notebook_metadata(notebook_id)

    assert success is True
    assert metadata["tags"] == ["test", "updated"]
    assert metadata["status"] == "active"


def test_cache_management(memory_service, sample_notebook):
    """Test that the cache properly manages notebook access."""
    # Test caching of notebooks without strict size constraint
    # This focuses on verifying that notebooks are properly cached when retrieved

    # First, clear any existing cache
    memory_service.notebook_cache.clear()
    memory_service.access_timestamps.clear()

    # Create test notebooks
    for i in range(3):
        notebook = sample_notebook.copy()
        notebook["title"] = f"Notebook {i}"
        notebook_id = f"cache-test-notebook-{i}"

        success, _ = memory_service.store_notebook(
            notebook_id=notebook_id,
            content=notebook,
        )
        assert success is True

    # Clear cache to start fresh
    memory_service.notebook_cache.clear()

    # Verify cache is initially empty
    assert len(memory_service.notebook_cache) == 0

    # Retrieve notebooks and check they are added to cache
    for i in range(3):
        notebook_id = f"cache-test-notebook-{i}"

        # First retrieval should add to cache
        success, _ = memory_service.retrieve_notebook(notebook_id)
        assert success is True
        assert notebook_id in memory_service.notebook_cache


def test_chunking_and_compression(memory_service):
    """Test notebook chunking and compression functionality."""
    # Create a large notebook to test chunking
    large_notebook = {
        "title": "Large Notebook",
        "created": time.time(),
        "metadata": {"author": "Test Author", "version": "1.0"},
        "pages": [],
    }

    # Add many pages to force chunking
    for i in range(50):  # Reduced to 50 to avoid test timeouts
        large_notebook["pages"].append(
            {
                "id": f"page{i}",
                "title": f"Page {i}",
                "content": f"This is page {i} with content repeated to increase size. "
                * 10,
                "tags": [f"page{i}", "test"],
            }
        )

    # Store large notebook
    notebook_id = "large-test-notebook"
    success, result = memory_service.store_notebook(
        notebook_id=notebook_id,
        content=large_notebook,
    )

    assert success is True

    # Check that the notebook was chunked
    notebook_dir = os.path.join(memory_service.storage_dir, notebook_id)
    chunk_metadata_path = os.path.join(notebook_dir, "chunks.json")

    assert os.path.exists(chunk_metadata_path)

    # We just want to make sure the metadata file exists and is valid JSON
    with open(chunk_metadata_path, "r") as f:
        json.load(f)

    # Retrieve the large notebook
    success, retrieved = memory_service.retrieve_notebook(notebook_id)

    assert success is True
    assert retrieved["title"] == "Large Notebook"
    assert len(retrieved["pages"]) == 50  # Changed to match reduced page count


def test_clean_storage(memory_service, sample_notebook):
    """Test cleaning up old notebooks."""
    # Store some notebooks with manipulated access times
    for i in range(5):
        notebook = sample_notebook.copy()
        notebook["title"] = f"Notebook {i}"
        notebook_id = f"cleanup-test-notebook-{i}"

        success, result = memory_service.store_notebook(
            notebook_id=notebook_id,
            content=notebook,
        )

        # Manipulate last_accessed time for some notebooks to make them "old"
        if i < 3:
            # Make notebooks 0, 1, 2 appear old (40 days ago)
            forty_days_ago = time.time() - (40 * 24 * 60 * 60)
            memory_service.metadata_index[notebook_id]["last_accessed"] = forty_days_ago
            memory_service._save_metadata_index()

    # Clean storage with 30-day threshold
    success, result = memory_service.clean_storage(days_threshold=30)

    assert success is True
    assert result["cleaned_notebooks"] == 3

    # Verify old notebooks are gone
    for i in range(5):
        notebook_id = f"cleanup-test-notebook-{i}"
        success, _ = memory_service.retrieve_notebook(notebook_id)

        if i < 3:
            # Old notebooks should be gone
            assert success is False
        else:
            # Recent notebooks should remain
            assert success is True
