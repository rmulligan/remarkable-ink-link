#!/usr/bin/env python3
"""Test Ollama vision model for handwriting recognition."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.inklink.adapters.ollama_vision_adapter import OllamaVisionAdapter  # noqa: E402


async def test_vision_handwriting():
    """Test vision model handwriting recognition."""
    adapter = OllamaVisionAdapter()

    # You can specify a test image path here
    test_image = "path/to/your/handwriting/image.png"

    if not os.path.exists(test_image) and len(sys.argv) > 1:
        test_image = sys.argv[1]

    if not os.path.exists(test_image):
        print("Please provide a valid image path as argument")
        print(f"Usage: {sys.argv[0]} <image_path>")
        return

    print(f"Testing handwriting recognition on: {test_image}")
    print("Using model: qwen2.5vl:32b-q4_K_M")
    print("-" * 50)

    try:
        # Test basic handwriting recognition
        result = await adapter.query_handwriting(test_image)
        print("Recognized text:")
        print(result)
        print("-" * 50)

        # Test with custom prompt
        custom_prompt = "This image contains handwritten mathematical equations. Please transcribe them accurately, using proper mathematical notation."
        custom_result = await adapter.query_vision(
            model="qwen2.5vl:32b-q4_K_M",
            prompt=custom_prompt,
            images=test_image,
            temperature=0.3,
        )
        print("Custom prompt result:")
        print(custom_result)

    except Exception as e:
        print(f"Error: {e}")


async def test_streaming():
    """Test streaming response from vision model."""
    adapter = OllamaVisionAdapter()

    test_image = sys.argv[1] if len(sys.argv) > 1 else "test_image.png"

    if not os.path.exists(test_image):
        print("No test image found for streaming test")
        return

    print("\nTesting streaming response:")
    print("-" * 50)

    try:
        async for chunk in adapter.stream_query_vision(
            model="qwen2.5vl:32b-q4_K_M",
            prompt="Describe this handwritten text in detail.",
            images=test_image,
            temperature=0.5,
        ):
            print(chunk, end="", flush=True)
        print("\n" + "-" * 50)
    except Exception as e:
        print(f"Streaming error: {e}")


async def list_available_models():
    """List available Ollama models."""
    adapter = OllamaVisionAdapter()

    print("Available Ollama models:")
    print("-" * 50)

    models = await adapter.list_models()
    for model in models:
        name = model.get("name", "Unknown")
        size = model.get("size", 0)
        size_gb = size / (1024**3)
        modified = model.get("modified_at", "Unknown")

        # Check if it's a vision model (rough heuristic)
        is_vision = any(x in name.lower() for x in ["vision", "vl", "multimodal", "mm"])
        vision_tag = " [VISION]" if is_vision else ""

        print(f"{name:<40} {size_gb:>8.1f} GB  {modified}{vision_tag}")


async def main():
    """Run all tests."""
    print("Ollama Vision Adapter Test")
    print("=" * 50)

    # List available models
    await list_available_models()
    print()

    # Test handwriting recognition if image provided
    if len(sys.argv) > 1:
        await test_vision_handwriting()
        await test_streaming()
    else:
        print("\nTo test handwriting recognition, provide an image path:")
        print(f"  python {sys.argv[0]} <image_path>")


if __name__ == "__main__":
    asyncio.run(main())
