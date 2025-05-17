#!/usr/bin/env python
"""
Claude Code Integration Demo

This script demonstrates how to use the Claude Code integration in InkLink
for various coding assistance tasks.
"""

import asyncio
import os
import sys
from pathlib import Path

from inklink.adapters.claude_code_adapter import ClaudeCodeAdapter
from inklink.agents.base.agent import AgentConfig
from inklink.agents.core.cloud_coder_agent import CloudCoderAgent
from inklink.config import CONFIG
from inklink.providers.claude_code_provider import ClaudeCodeProvider
from inklink.services.document_service import DocumentService
from inklink.services.llm_interface import UnifiedLLMInterface
from inklink.services.llm_service_manager import LLMServiceManager
from inklink.services.remarkable_service import RemarkableService

# Add the parent directory to the path so we can import inklink
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after path manipulation to satisfy flake8


async def main():
    """Main demo function."""
    print("=== Claude Code Integration Demo ===\n")

    # Initialize services
    print("Initializing services...")

    # Create LLM service manager
    service_manager = LLMServiceManager()

    # Get the unified LLM interface
    llm_interface = service_manager.get_llm_interface()

    # Check provider status
    print("\nProvider Status:")
    status = service_manager.get_llm_status()
    for provider, info in status.items():
        if isinstance(info, dict):
            available = info.get("available", False)
            is_cloud = info.get("is_cloud", False)
            print(f"  {provider}: {'✓' if available else '✗'} (Cloud: {is_cloud})")

    print("\n" + "=" * 50 + "\n")

    # Demo 1: Generate code from prompt
    print("Demo 1: Code Generation")
    print("Prompt: Generate a Python function to calculate factorial")

    success, code = llm_interface.generate_code(
        prompt="Generate a Python function to calculate factorial recursively with error handling",
        language="python",
        content_sensitivity="low",
    )

    if success:
        print(f"\nGenerated Code:\n{code}")
    else:
        print(f"Error: {code}")

    print("\n" + "=" * 50 + "\n")

    # Demo 2: Review code
    print("Demo 2: Code Review")
    sample_code = """
def process_data(data):
    result = []
    for i in range(len(data)):
        if data[i] > 0:
            result.append(data[i] * 2)
    return result
"""
    print(f"Code to review:\n{sample_code}")

    success, feedback = llm_interface.review_code(
        code=sample_code,
        language="python",
        instruction="Check for performance improvements and Python best practices",
    )

    if success:
        print("\nReview Feedback:")
        if isinstance(feedback, dict):
            for key, value in feedback.items():
                if key != "raw_feedback":
                    print(f"  {key}: {value}")
        else:
            print(feedback)
    else:
        print(f"Error: {feedback}")

    print("\n" + "=" * 50 + "\n")

    # Demo 3: Debug code
    print("Demo 3: Code Debugging")
    buggy_code = """
def divide_numbers(a, b):
    return a / b

result = divide_numbers(10, 0)
"""
    error_message = "ZeroDivisionError: division by zero"

    print(f"Buggy Code:\n{buggy_code}")
    print(f"Error: {error_message}\n")

    success, debug_info = llm_interface.debug_code(
        code=buggy_code, error_message=error_message
    )

    if success:
        print("Debug Analysis:")
        if isinstance(debug_info, dict):
            for key, value in debug_info.items():
                if value and key != "raw_response":
                    print(f"  {key}:")
                    print(f"    {value}\n")
        else:
            print(debug_info)
    else:
        print(f"Error: {debug_info}")

    print("\n" + "=" * 50 + "\n")

    # Demo 4: Best practices
    print("Demo 4: Best Practices Query")
    query = (
        "What are the best practices for handling errors in Python async/await code?"
    )
    print(f"Query: {query}\n")

    success, advice = llm_interface.ask_best_practices(query=query, language="python")

    if success:
        print(f"Best Practices Advice:\n{advice}")
    else:
        print(f"Error: {advice}")

    print("\n" + "=" * 50 + "\n")

    # Demo 5: Cloud Coder Agent
    print("Demo 5: Cloud Coder Agent")

    # Get required services
    claude_code_provider = service_manager.get_llm_provider("claude_code")

    if claude_code_provider:
        # Create agent configuration
        agent_config = AgentConfig(
            name="cloud_coder",
            description="Cloud-based coding assistant using Claude Code",
            version="1.0.0",
            capabilities=[
                "code_generation",
                "code_review",
                "debugging",
                "best_practices",
                "summarization",
            ],
            mcp_enabled=True,
        )

        # Initialize the Cloud Coder agent
        cloud_coder = CloudCoderAgent(
            config=agent_config,
            claude_code_provider=claude_code_provider,
            llm_interface=llm_interface,
            remarkable_service=RemarkableService(
                CONFIG["RMAPI_PATH"], CONFIG["RM_FOLDER"]
            ),
            document_service=DocumentService(
                CONFIG["TEMP_DIR"], CONFIG["DRAWJ2D_PATH"]
            ),
        )

        # Start the agent
        await cloud_coder.start()

        # Test a request
        response = await cloud_coder.handle_request(
            {
                "type": "generate_code",
                "prompt": "Create a simple async web server in Python",
                "language": "python",
                "upload_to_remarkable": False,  # Don't upload in demo
            }
        )

        print("Agent Response:")
        if "error" in response:
            print(f"  Error: {response['error']}")
        else:
            print(f"  Code: {response.get('code', 'No code generated')[:200]}...")
            print(f"  Timestamp: {response.get('timestamp')}")

        # Get agent stats
        stats = cloud_coder.get_stats()
        print("\nAgent Stats:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # Stop the agent
        await cloud_coder.stop()
    else:
        print("Claude Code provider not available")

    print("\n" + "=" * 50 + "\n")

    # Demo 6: Privacy and routing
    print("Demo 6: Privacy-Aware Routing")

    # Update privacy settings
    service_manager.update_llm_privacy_settings(
        privacy_mode="strict", cloud_enabled=False
    )

    print("Privacy Mode: strict (cloud disabled)")

    # Try to generate code - should use local provider
    success, code = llm_interface.generate_code(
        prompt="Generate a simple hello world function", language="python"
    )

    if success:
        print(f"Generated (local): {code[:100]}...")
    else:
        print("No local provider available for code generation")

    # Reset privacy settings
    service_manager.update_llm_privacy_settings(
        privacy_mode="balanced", cloud_enabled=True
    )

    print("\nDemo completed!")


if __name__ == "__main__":
    asyncio.run(main())
