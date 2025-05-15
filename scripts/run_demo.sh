#!/bin/bash
# Simple wrapper script to run the demo with hardcoded API key

# Directly export the API key to ensure it's available
export LIMITLESS_API_KEY="sk-0b83e577-433d-4019-bfd5-b7979914cbde"

# Run the demo script with verbose output
echo "Running demo with API key: ${LIMITLESS_API_KEY}"
bash -x scripts/run_limitless_demo.sh
