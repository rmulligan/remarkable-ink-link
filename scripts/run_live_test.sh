#!/bin/bash
# Run the full live test of Claude Penpal Service

# Set environment variables
export INKLINK_RMAPI=${INKLINK_RMAPI:-"./local-rmapi"}
export CLAUDE_COMMAND=${CLAUDE_COMMAND:-"claude"}
export CLAUDE_MODEL=${CLAUDE_MODEL:-"claude-3-opus-20240229"}

# Get current directory
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
cd "$SCRIPT_DIR" || exit 1

# Show usage if requested
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Runs a full live test of the Claude Penpal Service with a real reMarkable notebook."
  echo ""
  echo "Options:"
  echo "  --tag TAG        Tag to look for in notebooks (default: Lilly)"
  echo "  --wait SECONDS   How long to wait for processing (default: 120 seconds)"
  echo "  --verbose, -v    Enable verbose logging"
  echo "  --help, -h       Show this help message"
  exit 0
fi

echo "Starting full live test of Claude Penpal Service..."
echo "Ensure you have a reMarkable notebook with content tagged with #Lilly"
echo ""

# Run the test script
python run_live_penpal_test.py "$@"

# Check exit code
if [ $? -eq 0 ]; then
  echo "✅ Live test completed successfully!"
else
  echo "❌ Live test failed!"
fi