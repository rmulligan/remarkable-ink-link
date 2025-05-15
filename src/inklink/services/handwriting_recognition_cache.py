"""Caching layer for handwriting recognition service.

This module provides a caching mechanism for handwriting recognition results,
helping to reduce duplicate API calls and improve performance.
"""

import os
import json
import hashlib
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class HandwritingRecognitionCache:
    """Cache for handwriting recognition results."""

    def __init__(self, cache_dir: str, max_age_seconds: int = 3600 * 24 * 7):
        """
        Initialize the cache.

        Args:
            cache_dir: Directory to store cache files
            max_age_seconds: Maximum age of cache entries in seconds (default: 7 days)
        """
        self.cache_dir = cache_dir
        self.max_age_seconds = max_age_seconds

        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)

        # Cleanup on initialization
        self._cleanup_cache()

        logger.info(f"Handwriting recognition cache initialized at {cache_dir}")

    def _compute_stroke_hash(self, strokes: List[Dict[str, Any]]) -> str:
        """
        Compute a hash for stroke data to use as cache key.
        The hash is based on the relevant stroke data (x, y, pressure),
        ignoring timestamps and other metadata.

        Args:
            strokes: List of stroke dictionaries

        Returns:
            Hash string representing the strokes
        """
        # Create a serializable representation of the essential stroke data
        # We only care about x, y, and pressure values for recognition
        serializable_strokes = []

        for stroke in strokes:
            serializable_stroke = {
                "x": stroke.get("x", []),
                "y": stroke.get("y", []),
                "p": (
                    stroke.get("pressure", [])
                    if stroke.get("pressure")
                    else stroke.get("p", [])
                ),
            }
            serializable_strokes.append(serializable_stroke)

        # Convert to JSON string and compute hash
        strokes_json = json.dumps(serializable_strokes, sort_keys=True)
        return hashlib.sha256(strokes_json.encode()).hexdigest()

    def _get_cache_path(
        self, stroke_hash: str, content_type: str, language: str
    ) -> str:
        """
        Get the path to the cache file for the given parameters.

        Args:
            stroke_hash: Hash of the strokes
            content_type: Content type (Text, Math, Diagram, etc.)
            language: Language code

        Returns:
            Path to the cache file
        """
        filename = f"{stroke_hash}_{content_type}_{language}.json"
        return os.path.join(self.cache_dir, filename)

    def get(
        self, strokes: List[Dict[str, Any]], content_type: str, language: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached result for the given strokes, content type, and language.

        Args:
            strokes: List of stroke dictionaries
            content_type: Content type (Text, Math, Diagram, etc.)
            language: Language code

        Returns:
            Cached result or None if not found or expired
        """
        # Compute hash for strokes
        stroke_hash = self._compute_stroke_hash(strokes)

        # Get cache file path
        cache_path = self._get_cache_path(stroke_hash, content_type, language)

        # Check if cache file exists
        if not os.path.exists(cache_path):
            return None

        try:
            # Read cache file
            with open(cache_path, "r") as f:
                cache_data = json.load(f)

            # Check if cache is expired
            timestamp = cache_data.get("timestamp", 0)
            current_time = time.time()

            if current_time - timestamp > self.max_age_seconds:
                logger.info(f"Cache expired for {stroke_hash}")
                # Remove expired cache
                os.remove(cache_path)
                return None

            # Cache hit
            logger.info(f"Cache hit for {stroke_hash}")
            return cache_data.get("result")

        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
            return None

    def put(
        self,
        strokes: List[Dict[str, Any]],
        content_type: str,
        language: str,
        result: Dict[str, Any],
    ) -> bool:
        """
        Store recognition result in cache.

        Args:
            strokes: List of stroke dictionaries
            content_type: Content type (Text, Math, Diagram, etc.)
            language: Language code
            result: Recognition result to cache

        Returns:
            True if stored successfully, False otherwise
        """
        # Compute hash for strokes
        stroke_hash = self._compute_stroke_hash(strokes)

        # Get cache file path
        cache_path = self._get_cache_path(stroke_hash, content_type, language)

        try:
            # Create cache data with timestamp
            cache_data = {
                "timestamp": time.time(),
                "result": result,
                "metadata": {
                    "content_type": content_type,
                    "language": language,
                    "stroke_count": len(strokes),
                    "point_count": sum(len(s.get("x", [])) for s in strokes),
                },
            }

            # Write to cache file
            with open(cache_path, "w") as f:
                json.dump(cache_data, f)

            logger.info(f"Cached result for {stroke_hash}")
            return True

        except Exception as e:
            logger.warning(f"Error writing to cache: {e}")
            return False

    def invalidate(
        self, strokes: List[Dict[str, Any]], content_type: str, language: str
    ) -> bool:
        """
        Invalidate cache entry for the given parameters.

        Args:
            strokes: List of stroke dictionaries
            content_type: Content type (Text, Math, Diagram, etc.)
            language: Language code

        Returns:
            True if invalidated successfully, False otherwise
        """
        # Compute hash for strokes
        stroke_hash = self._compute_stroke_hash(strokes)

        # Get cache file path
        cache_path = self._get_cache_path(stroke_hash, content_type, language)

        # Remove cache file if it exists
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                logger.info(f"Invalidated cache for {stroke_hash}")
                return True
            except Exception as e:
                logger.warning(f"Error invalidating cache: {e}")
                return False

        return True  # Nothing to invalidate

    def _cleanup_cache(self) -> int:
        """
        Clean up expired cache entries.

        Returns:
            Number of cache entries removed
        """
        removed_count = 0
        current_time = time.time()

        # Iterate through cache files
        for cache_file in os.listdir(self.cache_dir):
            cache_path = os.path.join(self.cache_dir, cache_file)

            # Skip directories
            if os.path.isdir(cache_path):
                continue

            try:
                # Read cache file
                with open(cache_path, "r") as f:
                    cache_data = json.load(f)

                # Check if cache is expired
                timestamp = cache_data.get("timestamp", 0)

                if current_time - timestamp > self.max_age_seconds:
                    # Remove expired cache
                    os.remove(cache_path)
                    removed_count += 1

            except Exception:
                # If there's an error reading the file, remove it
                try:
                    os.remove(cache_path)
                    removed_count += 1
                except Exception:
                    pass

        if removed_count > 0:
            logger.info(f"Removed {removed_count} expired cache entries")

        return removed_count

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of cache entries removed
        """
        removed_count = 0

        # Iterate through cache files
        for cache_file in os.listdir(self.cache_dir):
            cache_path = os.path.join(self.cache_dir, cache_file)

            # Skip directories
            if os.path.isdir(cache_path):
                continue

            try:
                # Remove cache file
                os.remove(cache_path)
                removed_count += 1
            except Exception:
                pass

        logger.info(f"Cleared {removed_count} cache entries")
        return removed_count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.

        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "cache_dir": self.cache_dir,
            "max_age_seconds": self.max_age_seconds,
            "entry_count": 0,
            "total_size_bytes": 0,
            "content_types": {},
            "languages": {},
        }

        # Iterate through cache files
        for cache_file in os.listdir(self.cache_dir):
            cache_path = os.path.join(self.cache_dir, cache_file)

            # Skip directories
            if os.path.isdir(cache_path):
                continue

            try:
                # Get file size
                file_size = os.path.getsize(cache_path)
                stats["total_size_bytes"] += file_size
                stats["entry_count"] += 1

                # Read cache file to get metadata
                with open(cache_path, "r") as f:
                    cache_data = json.load(f)

                # Extract metadata
                metadata = cache_data.get("metadata", {})
                content_type = metadata.get("content_type", "unknown")
                language = metadata.get("language", "unknown")

                # Update content type stats
                stats["content_types"][content_type] = (
                    stats["content_types"].get(content_type, 0) + 1
                )

                # Update language stats
                stats["languages"][language] = stats["languages"].get(language, 0) + 1

            except Exception:
                pass

        return stats
