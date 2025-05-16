#!/usr/bin/env python
"""
Simple test to check Limitless API connectivity.
"""
from pprint import pprint

import requests

# API key
API_KEY = "sk-0b83e577-433d-4019-bfd5-b7979914cbde"
BASE_URL = "https://api.limitless.ai"


def test_direct_api():
    """Test API by making direct requests."""
    print(f"Using API key: {API_KEY[:4]}...{API_KEY[-4:]}")

    # Headers
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    }

    # Get life logs
    print("\nFetching life logs:")
    response = requests.get(
        f"{BASE_URL}/v1/lifelogs", headers=headers, params={"limit": 3}
    )

    print(f"Response status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("API Response:")
        pprint(data)

        # If we got logs, get details of first log
        if (
            data
            and "data" in data
            and isinstance(data["data"], list)
            and len(data["data"]) > 0
        ):
            log_id = data["data"][0].get("id")
            if log_id:
                print(f"\nFetching details for log {log_id}:")
                response = requests.get(
                    f"{BASE_URL}/v1/lifelogs/{log_id}", headers=headers
                )

                if response.status_code == 200:
                    log_data = response.json()
                    print("Log details:")
                    pprint(log_data)
                else:
                    print(f"Error fetching log details: {response.status_code}")
                    print(response.text)
    else:
        print(f"API request failed: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    test_direct_api()
