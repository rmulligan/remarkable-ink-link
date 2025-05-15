#!/usr/bin/env python3
"""
Simple test for Limitless API with the new API key
"""

import os
import json
import requests

def main():
    # Get API key from environment
    api_key = os.environ.get("LIMITLESS_API_KEY")
    if not api_key:
        print("LIMITLESS_API_KEY not found in environment.")
        return
    
    print(f"Using API key: {api_key[:4]}...{api_key[-4:]}")
    
    # Make a request to the Limitless API
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }
    
    # Get life logs
    print("\nFetching life logs from API...")
    response = requests.get(
        "https://api.limitless.ai/v1/lifelogs",
        headers=headers,
        params={"limit": 5}
    )
    
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response keys: {list(data.keys())}")
        
        # Print full response for examination
        print("Full response:")
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    main()