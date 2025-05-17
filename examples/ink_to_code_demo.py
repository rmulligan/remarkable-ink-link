#!/usr/bin/env python
"""
Ink-to-Code Demo Script

This script demonstrates the ink-to-code workflow:
1. Create a handwritten pseudocode example
2. Process it with code detection
3. Generate executable code
4. Upload the response back to reMarkable
"""

import logging
import os
import sys
import tempfile
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from inklink.services.document_service import DocumentService  # noqa: E402
from inklink.services.ink_to_code_service import InkToCodeService  # noqa: E402
from inklink.services.remarkable_service import RemarkableService  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_demo_pseudocode_notebook():
    """Create a demo notebook with handwritten pseudocode."""

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        document_service = DocumentService(temp_dir)

        # Create content with pseudocode examples
        content = {
            "title": "Pseudocode Examples",
            "structured_content": [
                {"type": "h1", "content": "Code Generation Demo"},
                {
                    "type": "paragraph",
                    "content": "This notebook demonstrates ink-to-code conversion.",
                },
                {"type": "h2", "content": "Example 1: Bubble Sort #code"},
                {
                    "type": "text",
                    "content": """function bubbleSort(array):
    for i from 0 to n-1:
        for j from 0 to n-i-1:
            if array[j] > array[j+1]:
                swap array[j] with array[j+1]
    return array
#code #python""",
                },
                {"type": "h2", "content": "Example 2: Fibonacci #code"},
                {
                    "type": "text",
                    "content": """algorithm fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)
#code #algorithm""",
                },
                {"type": "h2", "content": "Example 3: Binary Search #code"},
                {
                    "type": "text",
                    "content": """function binarySearch(arr, target):
    left = 0
    right = len(arr) - 1

    while left <= right:
        mid = (left + right) / 2

        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1
#code #javascript""",
                },
                {"type": "h2", "content": "Example 4: Stack Implementation #code"},
                {
                    "type": "text",
                    "content": """class Stack:
    initialize():
        items = []

    push(item):
        items.append(item)

    pop():
        if not isEmpty():
            return items.pop()

    peek():
        if not isEmpty():
            return items[-1]

    isEmpty():
        return len(items) == 0
#code #class #python""",
                },
            ],
        }

        # Create the document
        rm_path = document_service.create_rmdoc_from_content(
            url="", qr_path="", content=content
        )

        return rm_path


def demonstrate_ink_to_code():
    """Demonstrate the complete ink-to-code workflow."""

    logger.info("=== Ink-to-Code Demo ===")

    # Initialize services
    ink_to_code_service = InkToCodeService()
    remarkable_service = RemarkableService()

    # Step 1: Create demo notebook
    logger.info("Step 1: Creating demo pseudocode notebook...")
    demo_notebook_path = create_demo_pseudocode_notebook()

    if not demo_notebook_path:
        logger.error("Failed to create demo notebook")
        return

    logger.info(f"Created demo notebook at: {demo_notebook_path}")

    # Step 2: Upload to reMarkable
    logger.info("Step 2: Uploading demo notebook to reMarkable...")
    success, message = remarkable_service.upload(
        demo_notebook_path, "Ink-to-Code Demo Notebook"
    )

    if not success:
        logger.error(f"Failed to upload notebook: {message}")
        return

    logger.info(f"Uploaded successfully: {message}")

    # Step 3: Process the notebook for code generation
    # In a real scenario, you would download the notebook after writing on it
    logger.info("Step 3: Processing notebook for code generation...")

    # Simulate processing the uploaded notebook
    success, result = ink_to_code_service.process_code_query(demo_notebook_path)

    if success:
        logger.info("Code generation successful!")
        logger.info(f"Recognized text: {result.get('recognized_text', '')[:100]}...")
        logger.info(f"Generated code: {result.get('generated_code', '')[:100]}...")
        logger.info(f"Response uploaded: {result.get('upload_message', '')}")
    else:
        logger.error(f"Code generation failed: {result.get('error', 'Unknown error')}")

    # Clean up
    if os.path.exists(demo_notebook_path):
        os.remove(demo_notebook_path)


def demonstrate_code_detection():
    """Demonstrate code detection capabilities."""

    logger.info("=== Code Detection Demo ===")

    from inklink.services.code_recognition_service import CodeRecognitionService
    from inklink.services.handwriting_recognition_service import (
        HandwritingRecognitionService,
    )

    # Initialize services
    handwriting_service = HandwritingRecognitionService()
    code_recognition = CodeRecognitionService(handwriting_service)

    # Test texts
    test_texts = [
        "This is regular text without any code",
        "function calculate(x, y) { return x + y; }",
        "#code\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
        "Here's my algorithm:\n1. Start\n2. For each item in list\n3. Process item\n4. End",
        "// This is a comment\nlet x = 10;\nconst result = x * 2;",
    ]

    for i, text in enumerate(test_texts):
        logger.info(f"\nTest {i + 1}: {text[:50]}...")
        detection = code_recognition.detect_code_content(text)

        logger.info(f"Is code: {detection['is_code']}")
        logger.info(f"Confidence: {detection['confidence']:.2f}")
        logger.info(f"Tags: {detection['tags']}")
        logger.info(f"Patterns: {detection['patterns']}")
        logger.info(f"Language hints: {detection['language_hints']}")
        logger.info(f"Code blocks: {len(detection['blocks'])}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ink-to-Code Demo")
    parser.add_argument(
        "--mode",
        choices=["full", "detection"],
        default="full",
        help="Demo mode: full workflow or just detection",
    )

    args = parser.parse_args()

    if args.mode == "full":
        demonstrate_ink_to_code()
    else:
        demonstrate_code_detection()

    logger.info("\nDemo completed!")
