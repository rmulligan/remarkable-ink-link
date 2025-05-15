#!/bin/bash
# Simple test script for Limitless integration

# Set API key directly
API_KEY="sk-0b83e577-433d-4019-bfd5-b7979914cbde"
echo "Using API key: ${API_KEY:0:4}...${API_KEY: -4}"

# Bold and color text
bold=$(tput bold)
green=$(tput setaf 2)
yellow=$(tput setaf 3)
blue=$(tput setaf 4)
reset=$(tput sgr0)

echo "${bold}${blue}╔════════════════════════════════════════════════════════════╗${reset}"
echo "${bold}${blue}║               Limitless Integration Test                   ║${reset}"
echo "${bold}${blue}╚════════════════════════════════════════════════════════════╝${reset}"
echo ""

# Set up environment variables
export LIMITLESS_API_KEY="$API_KEY"
export LIMITLESS_SYNC_INTERVAL=900

echo "${bold}Configuration:${reset}"
echo "• Limitless API Key: ${API_KEY:0:4}...${API_KEY: -4}"
echo "• Sync Interval: ${LIMITLESS_SYNC_INTERVAL} seconds"
echo ""

# Check if we can make a direct API call
echo "${bold}Testing direct API connection...${reset}"
curl -s -H "X-API-Key: $API_KEY" "https://api.limitless.ai/v1/lifelogs?limit=1" | head -20
echo ""

# Run a test using pytest
echo "${bold}Running Limitless live tests...${reset}"
LIMITLESS_API_KEY="$API_KEY" poetry run pytest tests/test_limitless_live.py::TestLimitlessLiveIntegration::test_limitless_adapter_ping -v