#!/usr/bin/env python3
"""Test and compare handwriting recognition backends."""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.inklink.services.handwriting_recognition_service_v2 import (  # noqa: E402
    HandwritingRecognitionServiceV2,
    RecognitionBackend,
)


async def test_backend(
    service: HandwritingRecognitionServiceV2, image_path: str, backend_name: str
):
    """Test a specific backend."""
    print(f"\n{backend_name} Backend Test")
    print("-" * 50)

    start_time = time.time()
    try:
        result = await service.recognize_handwriting(image_path)
        end_time = time.time()

        if result:
            print(f"Recognition successful ({end_time - start_time:.2f}s)")
            print(
                f"Result: {result[:200]}..."
                if len(result) > 200
                else f"Result: {result}"
            )
        else:
            print("Recognition failed")

    except Exception as e:
        end_time = time.time()
        print(f"Error ({end_time - start_time:.2f}s): {e}")


async def compare_backends(image_path: str):
    """Compare all available backends."""
    print(f"Testing handwriting recognition on: {image_path}")
    print("=" * 70)

    # Test Ollama Vision
    ollama_service = HandwritingRecognitionServiceV2(
        backend=RecognitionBackend.OLLAMA_VISION
    )
    await test_backend(ollama_service, image_path, "Ollama Vision (qwen2.5vl)")

    # Test Claude Vision
    claude_service = HandwritingRecognitionServiceV2(
        backend=RecognitionBackend.CLAUDE_VISION
    )
    await test_backend(claude_service, image_path, "Claude Vision")

    # Test Auto mode
    auto_service = HandwritingRecognitionServiceV2(backend=RecognitionBackend.AUTO)
    await test_backend(auto_service, image_path, "Auto (Ollama → Claude fallback)")

    # Check backend info
    print("\nBackend Information")
    print("-" * 50)
    info = await auto_service.get_backend_info()
    print(f"Current backend: {info['backend']}")
    print(f"Available backends: {info['available_backends']}")
    if "ollama_vision_models" in info:
        print(f"Ollama vision models: {info['ollama_vision_models']}")


async def test_preprocessing(image_path: str):
    """Test image preprocessing and text extraction."""
    print("\nText Processing Test")
    print("=" * 70)

    service = HandwritingRecognitionServiceV2(backend=RecognitionBackend.OLLAMA_VISION)

    result = await service.recognize_handwriting(image_path)

    if result:
        lines = service.extract_lines(result)
        words = service.extract_words(result)
        language = service.detect_language(result)

        print(f"Full text: {result[:100]}...")
        print(f"Lines extracted: {len(lines)}")
        print(f"First 3 lines: {lines[:3]}")
        print(f"Words extracted: {len(words)}")
        print(f"First 10 words: {words[:10]}")
        print(f"Detected language: {language}")


async def batch_test(image_paths: list):
    """Test batch processing."""
    print("\nBatch Processing Test")
    print("=" * 70)

    service = HandwritingRecognitionServiceV2(backend=RecognitionBackend.OLLAMA_VISION)

    print(f"Processing {len(image_paths)} images...")
    start_time = time.time()

    results = service.recognize_batch(image_paths)

    end_time = time.time()
    print(f"Batch processing completed in {end_time - start_time:.2f}s")

    for i, (path, result) in enumerate(zip(image_paths, results)):
        print(f"\nImage {i + 1} ({os.path.basename(path)}):")
        if result:
            print(f"  {result[:100]}...")
        else:
            print("  Failed to recognize")


async def main():
    """Run all tests."""
    if len(sys.argv) < 2:
        print(
            "Usage: python test_handwriting_backends.py <image_path> [additional_images...]"
        )
        sys.exit(1)

    image_paths = sys.argv[1:]
    primary_image = image_paths[0]

    if not os.path.exists(primary_image):
        print(f"Error: Image not found: {primary_image}")
        sys.exit(1)

    # Compare backends
    await compare_backends(primary_image)

    # Test preprocessing
    await test_preprocessing(primary_image)

    # Test batch processing if multiple images provided
    if len(image_paths) > 1:
        await batch_test(image_paths)


if __name__ == "__main__":
    asyncio.run(main())
