#!/bin/bash
# Run the metadata fix verification script

# Set environment variables
export INKLINK_RMAPI=${INKLINK_RMAPI:-"./local-rmapi"}

# Show help if requested
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Runs verification test for the Claude Penpal Service metadata fix."
  echo ""
  echo "Options:"
  echo "  --notebook-id ID     Use a specific notebook ID"
  echo "  --notebook-name NAME Use a specific notebook name"
  echo "  --verbose, -v        Enable verbose logging"
  echo "  --no-cleanup         Don't remove temporary files"
  echo "  --help, -h           Show this help message"
  exit 0
fi

# Run the verification script
python verify_metadata_fix.py "$@"

# Check exit code
if [ $? -eq 0 ]; then
  echo "✅ Verification completed successfully!"
else
  echo "❌ Verification failed!"
fi