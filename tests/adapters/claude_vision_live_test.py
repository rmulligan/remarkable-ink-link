#!/usr/bin/env python
"""
Live test script for ClaudeVisionAdapter

This script tests the ClaudeVisionAdapter with real images and live Claude API calls
to verify recognition quality, performance, and handling of different content types.
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest

try:
    import cv2

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

import numpy as np
from PIL import Image

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from inklink.adapters.claude_vision_adapter import ClaudeVisionAdapter  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("claude_vision_test.log")],
)
logger = logging.getLogger("claude_vision_test")


class ClaudeVisionTester:
    """Test harness for the ClaudeVisionAdapter"""

    def __init__(
        self,
        test_images_dir: str,
        output_dir: str,
        claude_command: Optional[str] = None,
        model: Optional[str] = None,
        enable_parallel: bool = True,
        max_workers: int = 4,
    ):
        """
        Initialize the tester.

        Args:
            test_images_dir: Directory containing test images
            output_dir: Directory to save results
            claude_command: Command to invoke Claude CLI
            model: Claude model to use
            enable_parallel: Enable parallel processing
            max_workers: Maximum number of worker threads
        """
        self.test_images_dir = Path(test_images_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Initialize the adapter
        self.adapter = ClaudeVisionAdapter(
            claude_command=claude_command,
            model=model,
            enable_preprocessing=True,
            enable_parallel_processing=enable_parallel,
            max_parallel_workers=max_workers,
        )

        # Verify adapter is available
        if not self.adapter.is_available():
            raise RuntimeError(
                "ClaudeVisionAdapter is not available. Check Claude CLI installation."
            )

        logger.info(f"Initialized ClaudeVisionAdapter with model: {model or 'default'}")

        # Performance metrics
        self.metrics = {
            "total_time": 0,
            "page_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "content_types": {
                "text": {"count": 0, "success": 0, "time": 0},
                "math": {"count": 0, "success": 0, "time": 0},
                "diagram": {"count": 0, "success": 0, "time": 0},
            },
        }

    def find_test_images(self, content_type: Optional[str] = None) -> List[Path]:
        """
        Find test images in the test directory, optionally filtering by content type.

        Args:
            content_type: Optional content type to filter by (text, math, diagram)

        Returns:
            List of paths to test images
        """
        # Look for PNG, JPEG, and JPG files
        extensions = [".png", ".jpeg", ".jpg"]
        images = []

        for ext in extensions:
            if content_type:
                # Find images in content type subdirectory
                content_dir = self.test_images_dir / content_type
                if content_dir.exists():
                    images.extend(list(content_dir.glob(f"*{ext}")))
            else:
                # Find all images
                images.extend(list(self.test_images_dir.glob(f"**/*{ext}")))

        logger.info(
            f"Found {len(images)} test images{' for ' + content_type if content_type else ''}"
        )
        return images

    def detect_content_type_from_path(self, image_path: Path) -> str:
        """
        Determine content type based on image path.

        Args:
            image_path: Path to the image

        Returns:
            Content type (text, math, or diagram)
        """
        # Check if image is in a content type directory
        for content_type in ["text", "math", "diagram"]:
            if content_type in str(image_path):
                return content_type

        # Use the adapter's auto-detection
        return self.adapter.detect_content_type(str(image_path))

    def test_single_image(
        self, image_path: Path, expected_content_type: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Test processing a single image.

        Args:
            image_path: Path to the image
            expected_content_type: Expected content type (for validation)

        Returns:
            Tuple of (success, results)
        """
        # Determine content type
        content_type = expected_content_type or self.detect_content_type_from_path(
            image_path
        )

        logger.info(f"Testing {image_path.name} (content type: {content_type})")

        # Update metrics
        self.metrics["content_types"][content_type]["count"] += 1

        # Process the image
        start_time = time.time()
        success, result = self.adapter.process_image(
            image_path=str(image_path), content_type=content_type
        )
        processing_time = time.time() - start_time

        # Update metrics
        self.metrics["total_time"] += processing_time
        self.metrics["page_count"] += 1

        if success:
            self.metrics["success_count"] += 1
            self.metrics["content_types"][content_type]["success"] += 1
        else:
            self.metrics["failure_count"] += 1

        self.metrics["content_types"][content_type]["time"] += processing_time

        # Save the result
        output_path = self.output_dir / f"{image_path.stem}_{content_type}_result.txt"
        with open(output_path, "w") as f:
            f.write(result if success else f"FAILED: {result}")

        # Create a results object for analysis
        results = {
            "image_path": str(image_path),
            "content_type": content_type,
            "success": success,
            "result": result,
            "processing_time": processing_time,
            "output_path": str(output_path),
        }

        logger.info(
            f"Processed {image_path.name} in {processing_time:.2f}s: {'SUCCESS' if success else 'FAILED'}"
        )
        return success, results

    def test_multi_page(
        self,
        image_paths: List[Path],
        maintain_context: bool = True,
        content_types: Optional[List[str]] = None,
    ) -> Tuple[bool, Dict]:
        """
        Test processing multiple pages.

        Args:
            image_paths: List of paths to images
            maintain_context: Whether to maintain context between pages
            content_types: Optional list of content types

        Returns:
            Tuple of (success, results)
        """
        # Auto-detect content types if not provided
        if not content_types:
            content_types = [
                self.detect_content_type_from_path(path) for path in image_paths
            ]

        logger.info(f"Testing multi-page processing with {len(image_paths)} pages")
        logger.info(f"Content types: {content_types}")
        logger.info(f"Maintain context: {maintain_context}")

        # Update metrics for each content type
        for content_type in content_types:
            self.metrics["content_types"][content_type]["count"] += 1

        # Process the images
        start_time = time.time()
        success, result = self.adapter.process_multiple_images(
            image_paths=[str(path) for path in image_paths],
            maintain_context=maintain_context,
            content_types=content_types,
        )
        processing_time = time.time() - start_time

        # Update metrics
        self.metrics["total_time"] += processing_time
        self.metrics["page_count"] += len(image_paths)

        if success:
            self.metrics["success_count"] += 1
            # Each content type gets partial credit for success
            for content_type in set(content_types):
                # Count how many times this content type appears
                type_count = content_types.count(content_type)
                # Add proportional success
                self.metrics["content_types"][content_type]["success"] += type_count
        else:
            self.metrics["failure_count"] += 1

        # Distribute time proportionally among content types
        for content_type in set(content_types):
            type_count = content_types.count(content_type)
            type_fraction = type_count / len(content_types)
            self.metrics["content_types"][content_type]["time"] += (
                processing_time * type_fraction
            )

        # Save the result
        output_name = f"multi_page_{'context' if maintain_context else 'no_context'}"
        output_path = self.output_dir / f"{output_name}_result.txt"
        with open(output_path, "w") as f:
            f.write(result if success else f"FAILED: {result}")

        # Create a results object for analysis
        results = {
            "image_paths": [str(path) for path in image_paths],
            "content_types": content_types,
            "maintain_context": maintain_context,
            "success": success,
            "result": result,
            "processing_time": processing_time,
            "output_path": str(output_path),
        }

        logger.info(
            f"Processed {len(image_paths)} pages in {processing_time:.2f}s: {'SUCCESS' if success else 'FAILED'}"
        )
        return success, results

    def run_all_tests(self) -> Dict:
        """
        Run all tests and return results.

        Returns:
            Dictionary of test results and metrics
        """
        all_results = {"single_page": {}, "multi_page": {}, "metrics": {}}

        # Test individual content types
        for content_type in ["text", "math", "diagram"]:
            images = self.find_test_images(content_type)

            if not images:
                logger.warning(f"No test images found for content type: {content_type}")
                continue

            all_results["single_page"][content_type] = []

            for image_path in images:
                success, result = self.test_single_image(image_path, content_type)
                all_results["single_page"][content_type].append(result)

        # Test multi-page with different configurations
        # 1. Text-only multi-page with context
        text_images = self.find_test_images("text")
        if len(text_images) >= 2:
            success, result = self.test_multi_page(
                image_paths=text_images[:2],
                maintain_context=True,
                content_types=["text", "text"],
            )
            all_results["multi_page"]["text_with_context"] = result

        # 2. Mixed content types without context
        mixed_images = []
        mixed_content_types = []
        for content_type in ["text", "math", "diagram"]:
            images = self.find_test_images(content_type)
            if images:
                mixed_images.append(images[0])
                mixed_content_types.append(content_type)

        if len(mixed_images) >= 2:
            success, result = self.test_multi_page(
                image_paths=mixed_images,
                maintain_context=False,
                content_types=mixed_content_types,
            )
            all_results["multi_page"]["mixed_no_context"] = result

        # Add performance metrics
        all_results["metrics"] = self.calculate_metrics()
        self.print_metrics()

        return all_results

    def calculate_metrics(self) -> Dict:
        """
        Calculate and format performance metrics.

        Returns:
            Formatted metrics dictionary
        """
        metrics = self.metrics.copy()

        # Calculate additional metrics
        if metrics["page_count"] > 0:
            metrics["success_rate"] = (
                metrics["success_count"] / metrics["page_count"] * 100
            )
            metrics["average_time"] = metrics["total_time"] / metrics["page_count"]

            # Add per-content-type metrics
            for content_type, data in metrics["content_types"].items():
                if data["count"] > 0:
                    data["success_rate"] = data["success"] / data["count"] * 100
                    data["average_time"] = data["time"] / data["count"]

        return metrics

    def print_metrics(self):
        """Print formatted metrics to the console"""
        metrics = self.calculate_metrics()

        logger.info("=" * 50)
        logger.info("CLAUDE VISION ADAPTER TEST RESULTS")
        logger.info("=" * 50)
        logger.info(f"Total pages processed: {metrics['page_count']}")
        logger.info(f"Successful: {metrics['success_count']}")
        logger.info(f"Failed: {metrics['failure_count']}")

        if metrics["page_count"] > 0:
            logger.info(f"Success rate: {metrics['success_rate']:.1f}%")
            logger.info(
                f"Average processing time: {metrics['average_time']:.2f}s per page"
            )

        logger.info("-" * 50)
        logger.info("RESULTS BY CONTENT TYPE")
        for content_type, data in metrics["content_types"].items():
            if data["count"] > 0:
                logger.info(
                    f"{content_type.upper()}: {data['count']} pages, {data['success_rate']:.1f}% success, {data['average_time']:.2f}s avg"
                )
        logger.info("=" * 50)


def setup_test_images(test_dir: str):
    """
    Setup test images directory if it doesn't exist.
    Creates the directory structure and adds placeholder instructions.

    Args:
        test_dir: Path to test images directory
    """
    test_dir = Path(test_dir)

    # Create main directory
    test_dir.mkdir(exist_ok=True, parents=True)

    # Create content type subdirectories
    for content_type in ["text", "math", "diagram"]:
        content_dir = test_dir / content_type
        content_dir.mkdir(exist_ok=True)

        # Add placeholder file with instructions
        placeholder = content_dir / "README.txt"
        if not placeholder.exists():
            with open(placeholder, "w") as f:
                f.write(f"Place {content_type} test images in this directory.\n")
                f.write("Recommended format: PNG or JPEG images")
