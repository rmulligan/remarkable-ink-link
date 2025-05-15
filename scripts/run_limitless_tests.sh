#!/usr/bin/env bash

# Load environment variables directly from .env file
set -a
source ./.env
set +a

# Activate Python virtual environment directly
VENV_PATH="$(pwd)/.venv"
if [ -d "$VENV_PATH" ]; then
  source "$VENV_PATH/bin/activate"
  echo "Activated Python venv: $VIRTUAL_ENV"
else
  echo "Warning: Virtual environment not found at $VENV_PATH"
fi

echo "=== Running Limitless Tests with Environment Variables ==="
echo "LIMITLESS_API_KEY: ${LIMITLESS_API_KEY:0:4}...${LIMITLESS_API_KEY: -4}"
echo "NEO4J_URI: $NEO4J_URI"
echo "Python: $(which python)"
echo "==="

# Run the tests directly with the activated venv
if [ $# -eq 0 ]; then
  # Run all tests if no args provided
  python -m pytest tests/test_limitless_live.py -v
else
  # Apply test selection when arguments are provided
  python -m pytest "tests/test_limitless_live.py$@" -v
fi