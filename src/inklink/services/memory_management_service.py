"""Notebook memory management service for efficient storage and retrieval."""

import hashlib
import json
import logging
import os
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from inklink.config import CONFIG

logger = logging.getLogger(__name__)


class MemoryManagementService:
    """
    Service for efficiently managing notebook memory usage and storage.

    This service provides memory-efficient notebook storage and retrieval
    by implementing:
    1. Caching of frequently accessed notebooks
    2. Compression and decompression of notebook content
    3. Chunking of large notebooks for partial loading
    4. Metadata tracking for quick lookups
    5. Content-based deduplication
    """

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        cache_size: int = 10,
        compression_level: int = 6,
        chunk_size: int = 1024 * 1024,  # 1MB chunks
    ):
        """
        Initialize the memory management service.

        Args:
            storage_dir: Directory for persistent storage
            cache_size: Maximum number of notebooks to keep in memory
            compression_level: Compression level (0-9)
            chunk_size: Size of chunks for partial loading
        """
        # Set storage directory
        self.storage_dir = storage_dir or os.path.join(
            CONFIG.get("TEMP_DIR", "temp"), "notebook_storage"
        )

        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_dir, exist_ok=True)

        # Initialize cache and settings
        self.cache_size = cache_size
        self.compression_level = compression_level
        self.chunk_size = chunk_size

        # Cache for notebook content
        self.notebook_cache: Dict[str, Dict[str, Any]] = {}

        # Access tracker for LRU cache implementation
        self.access_timestamps: Dict[str, float] = {}

        # Metadata index for quick lookups
        self.metadata_index: Dict[str, Dict[str, Any]] = {}

        # Content hash index for deduplication
        self.content_hash_index: Dict[str, List[str]] = {}

        # Load metadata index
        self._load_metadata_index()

    def _load_metadata_index(self) -> None:
        """Load metadata index from storage directory."""
        metadata_path = os.path.join(self.storage_dir, "metadata_index.json")

        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    self.metadata_index = json.load(f)

                # Rebuild content hash index
                self._rebuild_content_hash_index()

                logger.info(f"Loaded metadata for {len(self.metadata_index)} notebooks")
            except Exception as e:
                logger.error(f"Error loading metadata index: {e}")
                # Initialize empty index if loading fails
                self.metadata_index = {}

    def _save_metadata_index(self) -> None:
        """Save metadata index to storage directory."""
        metadata_path = os.path.join(self.storage_dir, "metadata_index.json")

        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(self.metadata_index, f, indent=2)

            logger.debug(f"Saved metadata for {len(self.metadata_index)} notebooks")
        except Exception as e:
            logger.error(f"Error saving metadata index: {e}")

    def _rebuild_content_hash_index(self) -> None:
        """Rebuild content hash index from metadata index."""
        self.content_hash_index = {}

        for notebook_id, metadata in self.metadata_index.items():
            content_hash = metadata.get("content_hash")
            if content_hash:
                if content_hash not in self.content_hash_index:
                    self.content_hash_index[content_hash] = []

                self.content_hash_index[content_hash].append(notebook_id)

    def _compute_content_hash(self, content: Dict[str, Any]) -> str:
        """
        Compute hash of notebook content for deduplication.

        Args:
            content: Notebook content

        Returns:
            Content hash string
        """
        try:
            # Convert to canonical JSON representation
            canonical_json = json.dumps(content, sort_keys=True)

            # Compute hash
            return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        except Exception as e:
            logger.error(f"Error computing content hash: {e}")
            # Use timestamp as fallback
            return f"error-hash-{int(time.time())}"

    def _manage_cache(self, notebook_id: str = None) -> None:
        """
        Manage notebook cache to stay within size limits.

        Args:
            notebook_id: ID of notebook just accessed (to update timestamp)
        """
        # Update access timestamp for the notebook that was just accessed
        if notebook_id:
            self.access_timestamps[notebook_id] = time.time()

        # If cache is within size limit, no action needed
        if len(self.notebook_cache) <= self.cache_size:
            return

        # Sort notebooks by access time (oldest first)
        sorted_notebooks = sorted(self.access_timestamps.items(), key=lambda x: x[1])

        # Remove oldest notebooks until we're within cache size
        notebooks_to_remove = len(self.notebook_cache) - self.cache_size
        for i in range(notebooks_to_remove):
            if i >= len(sorted_notebooks):
                break

            notebook_id_to_remove = sorted_notebooks[i][0]

            # Remove from cache but keep timestamp in case it's accessed again
            if notebook_id_to_remove in self.notebook_cache:
                del self.notebook_cache[notebook_id_to_remove]
                logger.debug(f"Removed notebook {notebook_id_to_remove} from cache")

    def _compress_notebook(self, content: Dict[str, Any]) -> bytes:
        """
        Compress notebook content.

        Args:
            content: Notebook content

        Returns:
            Compressed binary data
        """
        try:
            import zlib

            # Convert to JSON string
            json_data = json.dumps(content)

            # Compress with zlib
            compressed_data = zlib.compress(
                json_data.encode("utf-8"), level=self.compression_level
            )

            return compressed_data
        except ImportError:
            logger.warning("zlib module not available, storing uncompressed data")
            return json.dumps(content).encode("utf-8")
        except Exception as e:
            logger.error(f"Error compressing notebook: {e}")
            return json.dumps(content).encode("utf-8")

    def _decompress_notebook(self, compressed_data: bytes) -> Dict[str, Any]:
        """
        Decompress notebook content.

        Args:
            compressed_data: Compressed binary data

        Returns:
            Notebook content
        """
        try:
            import zlib

            # Decompress with zlib
            json_data = zlib.decompress(compressed_data).decode("utf-8")

            # Parse JSON
            return json.loads(json_data)
        except ImportError:
            logger.warning("zlib module not available, assuming uncompressed data")
            return json.loads(compressed_data.decode("utf-8"))
        except Exception as e:
            logger.error(f"Error decompressing notebook: {e}")
            return {}

    def _chunk_notebook(self, content: Dict[str, Any]) -> List[bytes]:
        """
        Split notebook into chunks for partial loading.

        Args:
            content: Notebook content

        Returns:
            List of compressed chunks
        """
        try:
            # Compress the full notebook first
            compressed_data = self._compress_notebook(content)

            # Split into chunks
            chunks = []
            for i in range(0, len(compressed_data), self.chunk_size):
                chunk = compressed_data[i : i + self.chunk_size]
                chunks.append(chunk)

            return chunks
        except Exception as e:
            logger.error(f"Error chunking notebook: {e}")
            return [self._compress_notebook(content)]

    def _save_chunked_notebook(
        self, notebook_id: str, chunks: List[bytes]
    ) -> Tuple[bool, str]:
        """
        Save chunked notebook to storage.

        Args:
            notebook_id: Notebook identifier
            chunks: List of compressed chunks

        Returns:
            Tuple of (success, message)
        """
        try:
            # Create directory for notebook chunks
            notebook_dir = os.path.join(self.storage_dir, notebook_id)
            os.makedirs(notebook_dir, exist_ok=True)

            # Save each chunk
            for i, chunk in enumerate(chunks):
                chunk_path = os.path.join(notebook_dir, f"chunk_{i}.bin")
                with open(chunk_path, "wb") as f:
                    f.write(chunk)

            # Save metadata about chunks
            chunk_metadata = {
                "num_chunks": len(chunks),
                "chunk_size": self.chunk_size,
                "timestamp": time.time(),
            }

            chunk_metadata_path = os.path.join(notebook_dir, "chunks.json")
            with open(chunk_metadata_path, "w", encoding="utf-8") as f:
                json.dump(chunk_metadata, f)

            return True, f"Saved {len(chunks)} chunks to {notebook_dir}"
        except Exception as e:
            logger.error(f"Error saving chunked notebook: {e}")
            return False, str(e)

    def _load_chunked_notebook(self, notebook_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Load chunked notebook from storage.

        Args:
            notebook_id: Notebook identifier

        Returns:
            Tuple of (success, notebook_content)
        """
        try:
            # Get directory for notebook chunks
            notebook_dir = os.path.join(self.storage_dir, notebook_id)

            if not os.path.exists(notebook_dir):
                return False, {"error": f"Notebook {notebook_id} not found"}

            # Load metadata about chunks
            chunk_metadata_path = os.path.join(notebook_dir, "chunks.json")
            if not os.path.exists(chunk_metadata_path):
                return False, {"error": f"Chunk metadata for {notebook_id} not found"}

            with open(chunk_metadata_path, "r", encoding="utf-8") as f:
                chunk_metadata = json.load(f)

            num_chunks = chunk_metadata.get("num_chunks", 0)

            # Load and concatenate all chunks
            compressed_data = bytes()
            for i in range(num_chunks):
                chunk_path = os.path.join(notebook_dir, f"chunk_{i}.bin")

                if not os.path.exists(chunk_path):
                    return False, {"error": f"Chunk {i} for {notebook_id} not found"}

                with open(chunk_path, "rb") as f:
                    chunk_data = f.read()

                compressed_data += chunk_data

            # Decompress the concatenated data
            notebook_content = self._decompress_notebook(compressed_data)

            return True, notebook_content
        except Exception as e:
            logger.error(f"Error loading chunked notebook: {e}")
            return False, {"error": str(e)}

    def store_notebook(
        self, notebook_id: str, content: Dict[str, Any], metadata: Dict[str, Any] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Store a notebook with efficient memory management.

        Args:
            notebook_id: Unique identifier for the notebook
            content: Notebook content
            metadata: Additional metadata about the notebook

        Returns:
            Tuple of (success, result)
        """
        try:
            # Compute content hash for deduplication
            content_hash = self._compute_content_hash(content)

            # Check for existing notebooks with same content
            if content_hash in self.content_hash_index:
                identical_notebooks = self.content_hash_index[content_hash]
                logger.info(
                    f"Found {len(identical_notebooks)} notebooks with identical content"
                )

            # Prepare metadata
            full_metadata = {
                "id": notebook_id,
                "content_hash": content_hash,
                "size": len(json.dumps(content).encode("utf-8")),
                "created": time.time(),
                "last_accessed": time.time(),
            }

            # Add user-provided metadata
            if metadata:
                full_metadata.update(metadata)

            # Update metadata index
            self.metadata_index[notebook_id] = full_metadata
            self._save_metadata_index()

            # Update content hash index
            if content_hash not in self.content_hash_index:
                self.content_hash_index[content_hash] = []

            if notebook_id not in self.content_hash_index[content_hash]:
                self.content_hash_index[content_hash].append(notebook_id)

            # Split into chunks and save
            chunks = self._chunk_notebook(content)
            success, message = self._save_chunked_notebook(notebook_id, chunks)

            if not success:
                return False, {"error": message}

            # Add to cache
            self.notebook_cache[notebook_id] = content
            self.access_timestamps[notebook_id] = time.time()

            # Manage cache size
            self._manage_cache()

            return True, {
                "message": f"Notebook {notebook_id} stored successfully",
                "metadata": full_metadata,
            }
        except Exception as e:
            logger.error(f"Error storing notebook: {e}")
            return False, {"error": str(e)}

    def retrieve_notebook(
        self, notebook_id: str, partial: bool = False, section: str = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Retrieve a notebook with efficient memory management.

        Args:
            notebook_id: Unique identifier for the notebook
            partial: Whether to load only part of the notebook
            section: Section of the notebook to load

        Returns:
            Tuple of (success, notebook_content)
        """
        try:
            # Check if notebook exists in metadata index
            if notebook_id not in self.metadata_index:
                return False, {"error": f"Notebook {notebook_id} not found in index"}

            # Update access timestamp in metadata
            self.metadata_index[notebook_id]["last_accessed"] = time.time()
            self._save_metadata_index()

            # Check if notebook is already in cache
            if notebook_id in self.notebook_cache:
                logger.debug(f"Notebook {notebook_id} found in cache")

                # Update access timestamp for LRU cache
                self._manage_cache(notebook_id)

                # Return full notebook or partial section
                if partial and section:
                    if section in self.notebook_cache[notebook_id]:
                        return True, {
                            section: self.notebook_cache[notebook_id][section]
                        }
                    else:
                        return False, {
                            "error": f"Section {section} not found in notebook"
                        }
                else:
                    return True, self.notebook_cache[notebook_id]

            # Load notebook from storage
            success, notebook_content = self._load_chunked_notebook(notebook_id)

            if not success:
                return False, notebook_content  # Contains error message

            # Add to cache
            self.notebook_cache[notebook_id] = notebook_content
            self.access_timestamps[notebook_id] = time.time()

            # Manage cache size
            self._manage_cache()

            # Return full notebook or partial section
            if partial and section:
                if section in notebook_content:
                    return True, {section: notebook_content[section]}
                else:
                    return False, {"error": f"Section {section} not found in notebook"}
            else:
                return True, notebook_content
        except Exception as e:
            logger.error(f"Error retrieving notebook: {e}")
            return False, {"error": str(e)}

    def update_notebook(
        self, notebook_id: str, content: Dict[str, Any], metadata: Dict[str, Any] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update an existing notebook.

        Args:
            notebook_id: Unique identifier for the notebook
            content: Updated notebook content
            metadata: Updated metadata about the notebook

        Returns:
            Tuple of (success, result)
        """
        try:
            # Check if notebook exists in metadata index
            if notebook_id not in self.metadata_index:
                return False, {"error": f"Notebook {notebook_id} not found in index"}

            # Get old content hash
            old_hash = self.metadata_index[notebook_id].get("content_hash")

            # Compute new content hash
            new_hash = self._compute_content_hash(content)

            # Remove from old content hash index
            if old_hash and old_hash in self.content_hash_index:
                if notebook_id in self.content_hash_index[old_hash]:
                    self.content_hash_index[old_hash].remove(notebook_id)

                # Clean up empty lists
                if not self.content_hash_index[old_hash]:
                    del self.content_hash_index[old_hash]

            # Update metadata
            updated_metadata = self.metadata_index[notebook_id].copy()
            updated_metadata["content_hash"] = new_hash
            updated_metadata["last_updated"] = time.time()
            updated_metadata["last_accessed"] = time.time()
            updated_metadata["size"] = len(json.dumps(content).encode("utf-8"))

            # Add user-provided metadata
            if metadata:
                updated_metadata.update(metadata)

            # Update metadata index
            self.metadata_index[notebook_id] = updated_metadata
            self._save_metadata_index()

            # Update content hash index
            if new_hash not in self.content_hash_index:
                self.content_hash_index[new_hash] = []

            if notebook_id not in self.content_hash_index[new_hash]:
                self.content_hash_index[new_hash].append(notebook_id)

            # Delete old chunks
            notebook_dir = os.path.join(self.storage_dir, notebook_id)
            if os.path.exists(notebook_dir):
                shutil.rmtree(notebook_dir)

            # Split into chunks and save
            chunks = self._chunk_notebook(content)
            success, message = self._save_chunked_notebook(notebook_id, chunks)

            if not success:
                return False, {"error": message}

            # Update cache
            self.notebook_cache[notebook_id] = content
            self.access_timestamps[notebook_id] = time.time()

            # Manage cache size
            self._manage_cache()

            return True, {
                "message": f"Notebook {notebook_id} updated successfully",
                "metadata": updated_metadata,
            }
        except Exception as e:
            logger.error(f"Error updating notebook: {e}")
            return False, {"error": str(e)}

    def delete_notebook(self, notebook_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Delete a notebook.

        Args:
            notebook_id: Unique identifier for the notebook

        Returns:
            Tuple of (success, result)
        """
        try:
            # Check if notebook exists in metadata index
            if notebook_id not in self.metadata_index:
                return False, {"error": f"Notebook {notebook_id} not found in index"}

            # Get content hash
            content_hash = self.metadata_index[notebook_id].get("content_hash")

            # Remove from content hash index
            if content_hash and content_hash in self.content_hash_index:
                if notebook_id in self.content_hash_index[content_hash]:
                    self.content_hash_index[content_hash].remove(notebook_id)

                # Clean up empty lists
                if not self.content_hash_index[content_hash]:
                    del self.content_hash_index[content_hash]

            # Remove from metadata index
            deleted_metadata = self.metadata_index.pop(notebook_id, {})
            self._save_metadata_index()

            # Remove from cache
            if notebook_id in self.notebook_cache:
                del self.notebook_cache[notebook_id]

            # Remove from access timestamps
            if notebook_id in self.access_timestamps:
                del self.access_timestamps[notebook_id]

            # Delete notebook directory
            notebook_dir = os.path.join(self.storage_dir, notebook_id)
            if os.path.exists(notebook_dir):
                shutil.rmtree(notebook_dir)
                logger.debug(f"Deleted notebook directory: {notebook_dir}")

            return True, {
                "message": f"Notebook {notebook_id} deleted successfully",
                "deleted_metadata": deleted_metadata,
            }
        except Exception as e:
            logger.error(f"Error deleting notebook: {e}")
            return False, {"error": str(e)}

    def list_notebooks(
        self, filter_criteria: Dict[str, Any] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        List available notebooks with optional filtering.

        Args:
            filter_criteria: Dictionary of metadata criteria to filter by

        Returns:
            Tuple of (success, result with notebooks list)
        """
        try:
            notebooks = []

            # Apply filters if provided
            if filter_criteria:
                for notebook_id, metadata in self.metadata_index.items():
                    matched = True

                    for key, value in filter_criteria.items():
                        if key not in metadata or metadata[key] != value:
                            matched = False
                            break

                    if matched:
                        notebooks.append(metadata)
            else:
                # Return all notebooks
                notebooks = list(self.metadata_index.values())

            # Sort by last accessed time (most recent first)
            notebooks.sort(key=lambda x: x.get("last_accessed", 0), reverse=True)

            return True, {
                "count": len(notebooks),
                "notebooks": notebooks,
            }
        except Exception as e:
            logger.error(f"Error listing notebooks: {e}")
            return False, {"error": str(e)}

    def find_duplicate_notebooks(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Find notebooks with identical content.

        Returns:
            Tuple of (success, result with duplicate groups)
        """
        try:
            duplicates = {}

            for content_hash, notebook_ids in self.content_hash_index.items():
                if len(notebook_ids) > 1:
                    notebook_details = []

                    for notebook_id in notebook_ids:
                        if notebook_id in self.metadata_index:
                            notebook_details.append(self.metadata_index[notebook_id])

                    duplicates[content_hash] = notebook_details

            return True, {
                "duplicate_groups": len(duplicates),
                "duplicates": duplicates,
            }
        except Exception as e:
            logger.error(f"Error finding duplicate notebooks: {e}")
            return False, {"error": str(e)}

    def get_notebook_metadata(self, notebook_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get metadata for a specific notebook.

        Args:
            notebook_id: Unique identifier for the notebook

        Returns:
            Tuple of (success, metadata)
        """
        try:
            if notebook_id not in self.metadata_index:
                return False, {"error": f"Notebook {notebook_id} not found in index"}

            return True, self.metadata_index[notebook_id]
        except Exception as e:
            logger.error(f"Error getting notebook metadata: {e}")
            return False, {"error": str(e)}

    def update_notebook_metadata(
        self, notebook_id: str, metadata: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update metadata for a specific notebook.

        Args:
            notebook_id: Unique identifier for the notebook
            metadata: New metadata to update

        Returns:
            Tuple of (success, updated_metadata)
        """
        try:
            if notebook_id not in self.metadata_index:
                return False, {"error": f"Notebook {notebook_id} not found in index"}

            # Update metadata
            self.metadata_index[notebook_id].update(metadata)

            # Save metadata index
            self._save_metadata_index()

            return True, self.metadata_index[notebook_id]
        except Exception as e:
            logger.error(f"Error updating notebook metadata: {e}")
            return False, {"error": str(e)}

    def clean_storage(self, days_threshold: int = 30) -> Tuple[bool, Dict[str, Any]]:
        """
        Clean up old notebooks that haven't been accessed recently.

        Args:
            days_threshold: Number of days of inactivity before cleaning

        Returns:
            Tuple of (success, result)
        """
        try:
            current_time = time.time()
            seconds_threshold = days_threshold * 24 * 60 * 60

            notebooks_to_delete = []

            # Find notebooks older than threshold
            for notebook_id, metadata in self.metadata_index.items():
                last_accessed = metadata.get("last_accessed", 0)

                if current_time - last_accessed > seconds_threshold:
                    notebooks_to_delete.append(notebook_id)

            # Delete old notebooks
            deleted_count = 0
            for notebook_id in notebooks_to_delete:
                success, _ = self.delete_notebook(notebook_id)

                if success:
                    deleted_count += 1

            return True, {
                "cleaned_notebooks": deleted_count,
                "total_checked": len(self.metadata_index) + deleted_count,
            }
        except Exception as e:
            logger.error(f"Error cleaning storage: {e}")
            return False, {"error": str(e)}
