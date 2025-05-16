#!/usr/bin/env python3
"""
Demo script showing GitHub models validation in action.

This demonstrates how GitHub Copilot models can validate and enhance
Claude's responses for handwriting recognition and code understanding.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from inklink.adapters.ai_adapter import AIAdapter  # noqa: E402
from inklink.utils import setup_logging  # noqa: E402

# Setup logging
setup_logging("DEBUG")


def demo_basic_validation():
    """Demonstrate basic validation flow."""
    print("\n=== Basic Validation Demo ===")

    # Create adapter with validation
    adapter = AIAdapter(provider="anthropic", validation_provider="github")

    # Test prompt
    prompt = "Write a Python function to calculate factorial"

    print(f"\nPrompt: {prompt}")
    print("\nGenerating response with validation...")

    success, response = adapter.generate_completion(prompt)

    if success:
        print("\nComplete Response:")
        print(response)
    else:
        print(f"\nError: {response}")


def demo_code_validation():
    """Demonstrate code-specific validation."""
    print("\n=== Code Validation Demo ===")

    # Create adapter with GitHub validation
    adapter = AIAdapter(provider="anthropic", validation_provider="github")

    # Simulate handwritten code recognition
    handwritten_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""

    prompt = f"""
I've recognized this handwritten code. Please review it for correctness and suggest improvements:

```python
{handwritten_code}
```
"""

    print("\nHandwritten Code:")
    print(handwritten_code)
    print("\nValidating with GitHub models...")

    success, response = adapter.generate_completion(
        prompt,
        system_prompt="You are a code review expert. Focus on correctness, performance, and best practices.",
    )

    if success:
        print("\nValidated Response:")
        print(response)
    else:
        print(f"\nError: {response}")


def demo_technical_content():
    """Demonstrate technical content validation."""
    print("\n=== Technical Content Validation Demo ===")

    adapter = AIAdapter(provider="anthropic", validation_provider="github")

    prompt = """
Explain how async/await works in Python, including:
1. Event loop basics
2. Coroutines vs regular functions
3. Common pitfalls and best practices
"""

    print(f"\nPrompt: {prompt}")
    print("\nGenerating validated technical explanation...")

    success, response = adapter.generate_completion(prompt)

    if success:
        print("\nValidated Technical Content:")
        print(response[:500] + "..." if len(response) > 500 else response)
    else:
        print(f"\nError: {response}")


def demo_without_validation():
    """Demonstrate response without validation for comparison."""
    print("\n=== Response Without Validation ===")

    # Create adapter without validation
    adapter = AIAdapter(provider="anthropic")

    prompt = "Write a Python function to reverse a string"

    print(f"\nPrompt: {prompt}")
    print("\nGenerating response WITHOUT validation...")

    success, response = adapter.generate_completion(prompt)

    if success:
        print("\nResponse (No Validation):")
        print(response)
    else:
        print(f"\nError: {response}")


def check_environment():
    """Check if required environment variables are set."""
    print("=== Environment Check ===")

    required_vars = {
        "ANTHROPIC_API_KEY": "Claude API key",
        "GITHUB_TOKEN": "GitHub PAT with models:read",
    }

    missing = []
    for var, description in required_vars.items():
        if not os.environ.get(var):
            missing.append(f"{var} ({description})")
        else:
            print(f"✓ {var} is set")

    if missing:
        print("\n⚠️  Missing environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nPlease set these variables and try again.")
        return False

    return True


def main():
    """Run all demos."""
    print("GitHub Models Validation Demo")
    print("============================")

    if not check_environment():
        return

    try:
        # Run demos
        demo_basic_validation()
        demo_code_validation()
        demo_technical_content()
        demo_without_validation()

        print("\n=== Demo Complete ===")
        print("\nKey Benefits Demonstrated:")
        print("1. Cross-validation improves accuracy")
        print("2. GitHub models excel at code understanding")
        print("3. Ensemble approach provides comprehensive responses")
        print("4. Graceful degradation if validation fails")

    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
