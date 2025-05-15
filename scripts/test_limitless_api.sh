#!/bin/bash
#
# Test Limitless API Integration
#
# This script performs a comprehensive test of the Limitless API integration.
# It tests connectivity, fetching logs, pagination, and handles environment 
# variables appropriately.
#

set -e

# Bold and color text
bold=$(tput bold)
green=$(tput setaf 2)
yellow=$(tput setaf 3)
blue=$(tput setaf 4)
red=$(tput setaf 1)
reset=$(tput sgr0)

echo "${bold}${blue}╔════════════════════════════════════════════════════════════╗${reset}"
echo "${bold}${blue}║               InkLink Limitless API Test                   ║${reset}"
echo "${bold}${blue}╚════════════════════════════════════════════════════════════╝${reset}"
echo ""

# Get API key from environment, .env file, or argument
API_KEY=$1

# Try to load from .env file if exists
if [ -f .env ] && [ -z "$API_KEY" ]; then
  echo "Loading environment from .env file..."
  set -a
  source .env
  set +a
  API_KEY=$LIMITLESS_API_KEY
fi

# Try environment variable if still not set
if [ -z "$API_KEY" ]; then
  echo "Checking environment variables..."
  API_KEY=$LIMITLESS_API_KEY
fi

# Prompt for API key if still not set
if [ -z "$API_KEY" ]; then
  echo "${yellow}Limitless API key not found.${reset}"
  read -p "Please enter your Limitless API key: " API_KEY
  
  if [ -z "$API_KEY" ]; then
    echo "${bold}${red}No API key provided. Exiting.${reset}"
    exit 1
  fi
fi

# Activate virtual environment if available
if [ -d .venv ]; then
  echo "Activating Python virtual environment..."
  source .venv/bin/activate
fi

# Execute the Python test script with the API key
echo "Running Limitless API tests with key: ${API_KEY:0:4}...${API_KEY: -4}"

# Run the test directly using the Python script
python3 - << EOF
"""
LIMITLESS API TEST SCRIPT
Test the Limitless API integration with InkLink
"""
import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format="${bold}${blue}%(levelname)s:${reset} %(message)s")
logger = logging.getLogger()

# API configuration
API_KEY = "$API_KEY"
BASE_URL = "https://api.limitless.ai"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
TIMEOUT = 30  # seconds

def retry_with_backoff(func, *args, max_retries=MAX_RETRIES, **kwargs):
    """Retry a function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            # Add timeout to all requests
            if 'timeout' not in kwargs:
                kwargs['timeout'] = TIMEOUT

            response = func(*args, **kwargs)

            # Handle 504 Gateway Timeout
            if hasattr(response, 'status_code') and response.status_code == 504:
                raise requests.exceptions.RequestException(f"Gateway Timeout (504)")

            return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise

            wait_time = RETRY_DELAY * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)

def test_ping():
    """Test if the API is reachable."""
    print("\n${bold}Test 1: API Connection${reset}")
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    }
    
    try:
        response = retry_with_backoff(
            requests.get, f"{BASE_URL}/v1/lifelogs?limit=1", headers=headers
        )
        if response.status_code == 200:
            print("${green}✓ API connection successful${reset}")
            return True
        else:
            print(f"${red}✗ API connection failed (status: {response.status_code})${reset}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"${red}✗ API connection failed with exception: {e}${reset}")
        return False

def test_list_logs(limit=3):
    """Test fetching a list of logs."""
    print("\n${bold}Test 2: List Life Logs${reset}")
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    }
    
    try:
        response = retry_with_backoff(
            requests.get, f"{BASE_URL}/v1/lifelogs?limit={limit}", headers=headers
        )
        if response.status_code != 200:
            print(f"${red}✗ Failed to fetch logs (status: {response.status_code})${reset}")
            return False, None
        
        data = response.json()
        print("${green}✓ Successfully retrieved response${reset}")
        
        # Extract logs based on response format
        logs = []
        if "data" in data and isinstance(data["data"], dict) and "lifelogs" in data["data"]:
            logs = data["data"]["lifelogs"]
        elif "data" in data and isinstance(data["data"], list):
            logs = data["data"]
        elif "lifelogs" in data:
            logs = data["lifelogs"]
        
        if logs:
            print(f"Found {len(logs)} life logs:")
            for i, log in enumerate(logs):
                print(f"  {i+1}. {log.get('title', 'Untitled')} (ID: {log.get('id', 'Unknown')})")
        else:
            print("${yellow}No logs found in response${reset}")
        
        return True, logs
    except Exception as e:
        print(f"${red}✗ Failed to list logs with exception: {e}${reset}")
        return False, None

def test_pagination(limit=2, max_pages=3):
    """Test paginating through logs."""
    print("\n${bold}Test 3: Pagination${reset}")
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    }
    
    all_logs = []
    next_cursor = None
    page = 1
    
    try:
        while page <= max_pages:
            params = {"limit": limit}
            if next_cursor:
                params["cursor"] = next_cursor
            
            print(f"Fetching page {page}...")
            
            try:
                response = retry_with_backoff(
                    requests.get, f"{BASE_URL}/v1/lifelogs", headers=headers, params=params
                )
                
                if response.status_code != 200:
                    print(f"${red}✗ Failed to fetch page {page} (status: {response.status_code})${reset}")
                    break
                
                data = response.json()
                
                # Extract logs
                logs = []
                if "data" in data and isinstance(data["data"], dict) and "lifelogs" in data["data"]:
                    logs = data["data"]["lifelogs"]
                elif "data" in data and isinstance(data["data"], list):
                    logs = data["data"]
                elif "lifelogs" in data:
                    logs = data["lifelogs"]
                
                print(f"${green}✓ Retrieved {len(logs)} logs on page {page}${reset}")
                all_logs.extend(logs)
                
                # Check for next page
                next_cursor = None
                if "meta" in data and isinstance(data["meta"], dict):
                    meta = data["meta"]
                    if "lifelogs" in meta and isinstance(meta["lifelogs"], dict):
                        lifelogs_meta = meta["lifelogs"]
                        if "nextCursor" in lifelogs_meta and lifelogs_meta["nextCursor"]:
                            next_cursor = lifelogs_meta["nextCursor"]
                
                if not next_cursor:
                    print("${green}✓ No more pages to fetch${reset}")
                    break
                
                page += 1
                
            except Exception as e:
                print(f"${red}✗ Error fetching page {page}: {e}${reset}")
                break
    
        print(f"\nRetrieved a total of {len(all_logs)} logs across {page} pages")
        if len(all_logs) > 0:
            print("${green}✓ Pagination test successful${reset}")
            return True, all_logs
        else:
            print("${yellow}⚠ Pagination test completed but no logs were returned${reset}")
            return False, []
            
    except Exception as e:
        print(f"${red}✗ Pagination test failed with exception: {e}${reset}")
        return False, []

def main():
    """Run all tests."""
    print("\n${bold}${blue}LIMITLESS API INTEGRATION TEST${reset}\n")
    
    # Test 1: API Connection
    if not test_ping():
        print("\n${red}✗ API connection test failed. Aborting.${reset}")
        return False
    
    # Test 2: List Life Logs
    success, logs = test_list_logs(limit=3)
    if not success:
        print("\n${red}✗ Failed to fetch life logs. Aborting.${reset}")
        return False
    
    # Test 3: Pagination
    pagination_success, all_logs = test_pagination(limit=2, max_pages=3)
    
    # Summary
    print("\n${bold}${blue}TEST SUMMARY${reset}")
    print("${green}✓ API Connection${reset}")
    print("${green}✓ List Life Logs${reset}")
    
    if pagination_success:
        print("${green}✓ Pagination${reset}")
    else:
        print("${yellow}⚠ Pagination (partial success or issues)${reset}")
    
    print("\n${bold}${green}All critical tests completed successfully!${reset}")
    return True

if __name__ == "__main__":
    if not main():
        sys.exit(1)
EOF

echo ""
echo "${bold}${green}╔════════════════════════════════════════════════════════════╗${reset}"
echo "${bold}${green}║                    Test run completed                      ║${reset}"
echo "${bold}${green}╚════════════════════════════════════════════════════════════╝${reset}"