#!/usr/bin/env python
"""Script to fetch all Limitless life logs without any date restrictions."""

import json
from datetime import datetime, timedelta

import requests

# API key
API_KEY = "sk-0b83e577-433d-4019-bfd5-b7979914cbde"
BASE_URL = "https://api.limitless.ai"


def fetch_all_logs():
    """Fetch all logs without any date range restrictions."""
    print(f"Using API key: {API_KEY[:4]}...{API_KEY[-4:]}")

    # Headers
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    }

    # Try different endpoints and parameters

    # 1. Basic lifelogs endpoint with no filters
    print("\n1. Basic lifelogs endpoint (no filters):")
    response = requests.get(f"{BASE_URL}/v1/lifelogs", headers=headers)
    print_response(response)

    # 2. Try with explicit parameter for all dates (distant past)
    print("\n2. Lifelogs with explicit date in distant past:")
    from_date = (datetime.now() - timedelta(days=365 * 10)).isoformat()  # 10 years ago
    response = requests.get(
        f"{BASE_URL}/v1/lifelogs",
        headers=headers,
        params={"from": from_date, "limit": 50},
    )
    print_response(response)

    # 3. Try searching
    print("\n3. Lifelogs with search term:")
    response = requests.get(
        f"{BASE_URL}/v1/lifelogs",
        headers=headers,
        params={"q": ""},  # Empty search term to get all logs
    )
    print_response(response)

    # 4. Try the /logs endpoint (if available)
    print("\n4. Alternative /logs endpoint (if available):")
    try:
        response = requests.get(f"{BASE_URL}/v1/logs", headers=headers)
        print_response(response)
    except Exception as e:
        print(f"Error trying alternative endpoint: {e}")

    # 5. Try the user endpoint to get user information
    print("\n5. User information:")
    try:
        response = requests.get(f"{BASE_URL}/v1/user", headers=headers)
        print_response(response)
    except Exception as e:
        print(f"Error fetching user info: {e}")


def print_response(response):
    """Print API response details."""
    print(f"Status code: {response.status_code}")

    if response.status_code >= 400:
        print(f"Error response: {response.text}")
        return

    try:
        data = response.json()
        print(
            f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
        )

        # Check for logs in various formats
        logs = []
        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], list):
                logs = data["data"]
            elif (
                "data" in data
                and isinstance(data["data"], dict)
                and "lifelogs" in data["data"]
            ):
                logs = data["data"]["lifelogs"]
            elif "lifelogs" in data:
                logs = data["lifelogs"]

        print(
            f"Found {len(logs) if isinstance(logs, list) else 'unknown number of'} logs"
        )

        # Print full response for debugging
        print("Full response:")
        print(json.dumps(data, indent=2))

        # Print details of first few logs if any
        if isinstance(logs, list) and logs:
            print("\nLog details:")
            for i, log in enumerate(logs[:3]):  # Show up to 3 logs
                if isinstance(log, dict):
                    print(f"Log {i + 1}:")
                    print(f"  ID: {log.get('id', 'No ID')}")
                    print(f"  Title: {log.get('title', 'No Title')}")
                    print(f"  Created: {log.get('created_at', 'Unknown')}")
                    content = log.get("content", "")
                    if content and len(content) > 100:
                        content = content[:100] + "..."
                    print(f"  Content: {content}")
                else:
                    print(f"Log {i + 1}: {log} (type: {type(log)})")

            if len(logs) > 3:
                print(f"... and {len(logs) - 3} more logs")
    except Exception as e:
        print(f"Error parsing response: {e}")
        print(f"Raw response: {response.text[:500]}...")


if __name__ == "__main__":
    fetch_all_logs()
