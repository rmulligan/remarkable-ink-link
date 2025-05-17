#!/usr/bin/env python
"""
Demo script for Claude Code MCP integration.

This script demonstrates how to use Claude Code through the MCP
tools interface within InkLink.
"""

import json
from inklink.mcp.registry import get_registry, register_all_tools
from inklink.mcp.claude_code_tools import (
    claude_code_generate,
    claude_code_review,
    claude_code_debug,
    claude_code_best_practices,
    claude_code_summarize,
    claude_code_manage_session,
)


def demo_code_generation():
    """Demonstrate code generation via MCP."""
    print("\n1. Code Generation Demo")
    print("-" * 40)

    params = {
        "prompt": "Create a Python function that calculates the nth Fibonacci number using memoization",
        "language": "python",
        "context": "The function should be efficient for large values of n",
    }

    result = claude_code_generate(params)

    if result["success"]:
        print(f"Provider: {result['provider']}")
        print(f"Language: {result['language']}")
        print(f"Code:\n{result['code']}")
        print(f"Routing reasoning: {result['routing']['reasoning']}")
    else:
        print(f"Error: {result['error']}")


def demo_code_review():
    """Demonstrate code review via MCP."""
    print("\n2. Code Review Demo")
    print("-" * 40)

    code = """
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n-1)
"""

    params = {
        "code": code,
        "language": "python",
        "focus_areas": ["performance", "error handling", "readability"],
    }

    result = claude_code_review(params)

    if result["success"]:
        print(f"Provider: {result['provider']}")
        print(f"Review:\n{result['review']}")
        print(f"Issues: {result.get('issues', [])}")
        print(f"Improvements: {result.get('improvements', [])}")
    else:
        print(f"Error: {result['error']}")


def demo_debugging():
    """Demonstrate debugging via MCP."""
    print("\n3. Debugging Demo")
    print("-" * 40)

    buggy_code = """
def divide_numbers(a, b):
    return a / b

result = divide_numbers(10, 0)
"""

    params = {
        "code": buggy_code,
        "error_message": "ZeroDivisionError: division by zero",
        "expected_behavior": "Should handle division by zero gracefully",
        "language": "python",
    }

    result = claude_code_debug(params)

    if result["success"]:
        print(f"Provider: {result['provider']}")
        print(f"Analysis:\n{result['analysis']}")
        print(f"Fixes: {result.get('fixes', [])}")
        if result.get("fixed_code"):
            print(f"Fixed code:\n{result['fixed_code']}")
    else:
        print(f"Error: {result['error']}")


def demo_best_practices():
    """Demonstrate best practices via MCP."""
    print("\n4. Best Practices Demo")
    print("-" * 40)

    params = {
        "topic": "Python async/await patterns for web scraping",
        "language": "python",
        "context": "Building a high-performance web scraper",
        "level": "intermediate",
    }

    result = claude_code_best_practices(params)

    if result["success"]:
        print(f"Provider: {result['provider']}")
        print(f"Best Practices:\n{result['best_practices']}")
        print(f"Examples: {result.get('examples', [])}")
        print(f"Resources: {result.get('resources', [])}")
    else:
        print(f"Error: {result['error']}")


def demo_summarization():
    """Demonstrate technical summarization via MCP."""
    print("\n5. Technical Summarization Demo")
    print("-" * 40)

    technical_content = """
    Microservices architecture is an approach to developing a single application
    as a suite of small services, each running in its own process and communicating
    with lightweight mechanisms. These services are built around business capabilities
    and independently deployable by fully automated deployment machinery.
    """

    params = {
        "content": technical_content,
        "type": "architecture",
        "style": "brief",
        "focus": ["benefits", "challenges"],
    }

    result = claude_code_summarize(params)

    if result["success"]:
        print(f"Provider: {result['provider']}")
        print(f"Summary:\n{result['summary']}")
        print(f"Key Points: {result.get('key_points', [])}")
    else:
        print(f"Error: {result['error']}")


def demo_session_management():
    """Demonstrate session management via MCP."""
    print("\n6. Session Management Demo")
    print("-" * 40)

    # Create a new session
    create_params = {
        "action": "create",
        "metadata": {"user": "demo-user", "project": "fibonacci-optimization"},
    }

    result = claude_code_manage_session(create_params)

    if result["success"]:
        print(f"Created session: {result['session_id']}")
        print(f"Status: {result['status']}")

        # Get session status
        status_params = {
            "action": "status",
            "session_id": result["session_id"],
        }

        status_result = claude_code_manage_session(status_params)
        print(f"Session status: {status_result}")
    else:
        print(f"Error: {result['error']}")


def demo_mcp_registry():
    """Demonstrate MCP registry functionality."""
    print("\n7. MCP Registry Demo")
    print("-" * 40)

    # Get the registry and register all tools
    registry = get_registry()
    register_all_tools()

    # Check if Claude Code tools are registered
    claude_tools = [
        "claude_code_generate",
        "claude_code_review",
        "claude_code_debug",
        "claude_code_best_practices",
        "claude_code_summarize",
        "claude_code_manage_session",
    ]

    print("Registered Claude Code tools:")
    for tool_name in claude_tools:
        handler = registry.get_tool(tool_name)
        print(f"  - {tool_name}: {'✓' if handler else '✗'}")

    # Test handling a tool request through the registry
    print("\nTesting registry tool request:")
    test_params = {
        "prompt": "Hello, Claude Code!",
        "language": "python",
    }

    result = registry.handle_tool_request("claude_code_generate", test_params)
    print(f"Result: {json.dumps(result, indent=2)}")


def main():
    """Run all demo functions."""
    print("Claude Code MCP Integration Demo")
    print("=" * 40)

    # Ensure environment is set up
    print("\nNote: Ensure Claude Code CLI is installed and configured.")
    print("Set CLAUDE_CODE_COMMAND environment variable if needed.")

    demos = [
        demo_code_generation,
        demo_code_review,
        demo_debugging,
        demo_best_practices,
        demo_summarization,
        demo_session_management,
        demo_mcp_registry,
    ]

    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"Error in {demo.__name__}: {e}")
            import traceback

            traceback.print_exc()

    print("\nDemo complete!")


if __name__ == "__main__":
    main()
