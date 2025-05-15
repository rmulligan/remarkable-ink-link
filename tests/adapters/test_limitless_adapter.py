#!/usr/bin/env python
"""
Simple test script for Limitless adapter.
"""

import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))

from inklink.adapters.limitless_adapter import LimitlessAdapter  # noqa: E402


def main():
    """Main test function."""
    # API key
    api_key = "sk-0b83e577-433d-4019-bfd5-b7979914cbde"
    print(f"Using API key: {api_key[:4]}...{api_key[-4:]}")

    # Create adapter
    adapter = LimitlessAdapter(api_key=api_key)

    # Test ping
    print("\nTesting API connectivity (ping):")
    ping_result = adapter.ping()
    print(f"Ping result: {ping_result}")

    # Get life logs
    print("\nFetching recent life logs:")
    success, result = adapter.get_life_logs(limit=3)

    if success:
        if isinstance(result, dict) and "data" in result:
            logs = result.get("data", [])
            print(f"Successfully fetched {len(logs)} life logs")

            # Print result structure for debugging
            print(f"Result structure: {type(result)}")
            print(
                f"Keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}"
            )

            # Print basic info about logs
            if isinstance(logs, list):
                for i, log in enumerate(logs):
                    if isinstance(log, dict):
                        print(
                            f"- Log {i + 1}: {log.get('id', 'No ID')} - {log.get('title', 'No Title')}"
                        )
                    else:
                        print(f"- Log {i + 1}: {log} (type: {type(log)})")

                if logs and isinstance(logs[0], dict):
                    # Get a specific log
                    log_id = logs[0].get("id")
                    if log_id:
                        print("\nFetching specific log details:")
                        success, log = adapter.get_life_log_by_id(log_id)

                        if success and isinstance(log, dict):
                            print(f"Title: {log.get('title', 'No Title')}")
                            print(f"Created: {log.get('created_at', 'Unknown')}")
                            content = log.get("content", "")
                            if content and len(content) > 100:
                                content = content[:100] + "..."
                            print(f"Content: {content}")
                        else:
                            print(
                                f"Failed to get log details or invalid response: {log}"
                            )
            else:
                print(f"Logs is not a list: {logs} (type: {type(logs)})")
        else:
            print(f"Unexpected result format: {result} (type: {type(result)})")
    else:
        print(f"Error fetching logs: {result}")


if __name__ == "__main__":
    main()
