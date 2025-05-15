#!/bin/bash
# Run the Claude Penpal Service metadata fix test

# Set environment variables
export INKLINK_RMAPI=${INKLINK_RMAPI:-"./local-rmapi"}
export CLAUDE_COMMAND=${CLAUDE_COMMAND:-"claude"}
export CLAUDE_MODEL=${CLAUDE_MODEL:-"claude-3-opus-20240229"}

# Run the test script with verbose output
python test_claude_penpal_fix.py --verbose "$@"