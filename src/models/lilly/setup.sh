#!/bin/bash
# setup.sh
# Setup script for Lilly, the reMarkable Ink Link Assistant

# Set up environment
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Display header
echo "=================================="
echo "     Setting up Lilly 🖋️         "
echo "  reMarkable Ink Link Assistant  "
echo "=================================="
echo

# Check Python version
python_version=$(python3 --version 2>&1)
if [[ $? -ne 0 ]]; then
    echo "Error: Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi
echo "Using $python_version"

# Check if Claude CLI is installed
if ! command -v claude &> /dev/null; then
    echo "Error: Claude CLI not found. Please install the Claude terminal interface."
    echo "Visit: https://console.anthropic.com/docs/tools/claude-cli"
    exit 1
fi
echo "Claude CLI found"

# Check for rmapi
if ! command -v rmapi &> /dev/null; then
    echo "Warning: rmapi not found. reMarkable sync functionality will not work."
    echo "To install rmapi, visit: https://github.com/juruen/rmapi"
fi

# Check for rendering tools
has_renderer=false
if command -v rmscene &> /dev/null; then
    echo "rmscene found for rendering .rm files"
    has_renderer=true
elif command -v drawj2d &> /dev/null; then
    echo "drawj2d found for rendering .rm files"
    has_renderer=true
else
    echo "Warning: No reMarkable renderer found. Page rendering will not work."
    echo "Install rmscene or drawj2d for page rendering."
fi

# Create required directories
echo "Creating directory structure..."
mkdir -p "$SCRIPT_DIR/workspace/remarkable_sync"
mkdir -p "$SCRIPT_DIR/memories"

# Initialize Knowledge Graph
echo "Initializing knowledge graph..."
python3 "$SCRIPT_DIR/tools/initialize_knowledge_graph.py" || echo "Knowledge graph initialization failed, but continuing setup..."

# Set up MCP tools (placeholder for future automatic registration)
echo "Registering MCP tools..."
echo "Note: Automatic MCP tool registration not yet implemented."
echo "Please manually register tools if required."

# Make scripts executable
echo "Making scripts executable..."
chmod +x "$SCRIPT_DIR/start_lilly.sh"
chmod +x "$SCRIPT_DIR/tools/initialize_knowledge_graph.py"
chmod +x "$SCRIPT_DIR/tools/process_handwriting.py"
chmod +x "$SCRIPT_DIR/tools/sync_remarkable.py"

# Completion
echo
echo "Setup complete! ✅"
echo
echo "To start Lilly, run:"
echo "  ./start_lilly.sh"
echo
echo "For more information, see:"
echo "  ./README.md"
echo
echo "=================================="