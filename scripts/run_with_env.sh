#!/usr/bin/env bash

# Load environment variables directly from .env file
set -a
source ./.env
set +a

# Activate Python virtual environment
VENV_PATH="$(pwd)/.venv"
if [ -d "$VENV_PATH" ]; then
  source "$VENV_PATH/bin/activate"
  echo "Activated Python venv: $VIRTUAL_ENV"
fi

# Show loaded environment variables
echo "=== Environment Variables ==="
echo "LIMITLESS_API_KEY: ${LIMITLESS_API_KEY:0:4}...${LIMITLESS_API_KEY: -4}"
echo "NEO4J_URI: $NEO4J_URI"
echo "=== Running Command ==="

# Execute the command that was passed to the script
"$@"