#!/bin/bash
# Start the Lilly monitoring service for reMarkable notebooks tagged with 'Lilly'

# Set up environment
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PARENT_DIR="$( cd "$SCRIPT_DIR/.." &> /dev/null && pwd )"

# Display header
echo "=================================="
echo "     Starting Lilly Monitor 🖋️   "
echo "  reMarkable Ink Link Assistant  "
echo "=================================="
echo

# Default options
TAG="Lilly"
INTERVAL=60
CLAUDE_COMMAND="claude"
LILLY_WORKSPACE="$SCRIPT_DIR"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --tag=*)
            TAG="${1#*=}"
            shift
            ;;
        --interval=*)
            INTERVAL="${1#*=}"
            shift
            ;;
        --claude-command=*)
            CLAUDE_COMMAND="${1#*=}"
            shift
            ;;
        --once)
            ONCE_FLAG="--once"
            shift
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

# Check if src/inklink/main.py exists
if [ ! -f "$PARENT_DIR/src/inklink/main.py" ]; then
    echo "Error: Could not find main.py in expected location"
    echo "Expected: $PARENT_DIR/src/inklink/main.py"
    exit 1
fi

# Create log directory
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# Start the monitor using the main CLI
echo "Starting Lilly monitor with the following settings:"
echo "- Tag: $TAG"
echo "- Polling interval: $INTERVAL seconds"
echo "- Claude command: $CLAUDE_COMMAND"
echo "- Lilly workspace: $LILLY_WORKSPACE"
echo

# Use Poetry to run the main.py script with the lilly command
cd "$PARENT_DIR"
poetry run python -m src.inklink.main lilly \
    --tag="$TAG" \
    --interval="$INTERVAL" \
    --claude-command="$CLAUDE_COMMAND" \
    --lilly-workspace="$LILLY_WORKSPACE" \
    $ONCE_FLAG 2>&1 | tee "$LOG_DIR/lilly_monitor_$(date +%Y%m%d_%H%M%S).log"

# The monitor will run in the foreground, so this script will block until it's stopped