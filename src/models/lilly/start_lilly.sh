#!/bin/bash
# start_lilly.sh
# Script to start Lilly assistant with proper configuration

# Set up environment
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
CONFIG_DIR="$SCRIPT_DIR/config"
WORKSPACE_DIR="$SCRIPT_DIR/workspace"
MEMORIES_DIR="$SCRIPT_DIR/memories"
TOOLS_DIR="$SCRIPT_DIR/tools"

# Display header
echo "=================================="
echo "     Initializing Lilly 🖋️       "
echo "  reMarkable Ink Link Assistant  "
echo "=================================="
echo

# Check if required directories exist
for dir in "$CONFIG_DIR" "$WORKSPACE_DIR" "$MEMORIES_DIR" "$TOOLS_DIR"; do
    if [ ! -d "$dir" ]; then
        echo "Error: Required directory not found: $dir"
        echo "Creating missing directory..."
        mkdir -p "$dir"
    fi
done

# Check if the neo4j knowledge graph service is available via MCP
echo "Checking MCP connections..."
claude --mcp

# Prepare Lilly's specific Claude instructions
LILLY_INSTRUCTIONS="$CONFIG_DIR/lilly_persona.md"
if [ ! -f "$LILLY_INSTRUCTIONS" ]; then
    echo "Error: Lilly's persona file not found at $LILLY_INSTRUCTIONS"
    exit 1
fi

# Determine if this is the first run by checking if lilly_knowledge DB exists
FIRST_RUN=true
DB_CHECK=$(claude --no-tty << EOF
Using the neo4j-knowledge MCP tool, please get the current database name.
EOF
)

if [[ "$DB_CHECK" == *"lilly_knowledge"* ]]; then
    FIRST_RUN=false
fi

# Initialize the knowledge graph database for Lilly if needed
if [ "$FIRST_RUN" = true ]; then
    echo "First run detected. Initializing Lilly's knowledge graph..."

    # Switch to Lilly's knowledge graph DB
    claude --no-tty << EOF
Using the neo4j-knowledge MCP tool, please switch to a database named "lilly_knowledge"
and create it if it doesn't exist. Then, confirm the current database name.
EOF

    # Run the initialization script
    echo "Setting up initial entity types and relationships..."
    "$TOOLS_DIR/initialize_knowledge_graph.py"

    # Store tool usage information in the memory bank
    echo "Storing tool documentation in memory bank..."
    claude --no-tty << EOF
Using the memory-bank-mcp MCP tool, please write a new memory with this information:
- projectName: "lilly"
- fileName: "tool_documentation.md"
- content from file: "$MEMORIES_DIR/tool_usage.md"
EOF

    # Store workflow examples in the memory bank
    echo "Storing workflow examples in memory bank..."
    claude --no-tty << EOF
Using the memory-bank-mcp MCP tool, please write a new memory with this information:
- projectName: "lilly"
- fileName: "workflow_examples.md"
- content from file: "$MEMORIES_DIR/workflow_examples.md"
EOF

else
    echo "Lilly's knowledge graph already initialized. Switching to database..."
    claude --no-tty << EOF
Using the neo4j-knowledge MCP tool, please switch to a database named "lilly_knowledge".
EOF
fi

echo
echo "Starting Lilly with Claude terminal interface..."
echo "Use CTRL+C to exit"
echo

# Start Claude with Lilly's configuration and memory access
cat << EOF > "$WORKSPACE_DIR/session_start.md"
# Lilly Session Started

Welcome! I'm Lilly, your reMarkable Ink Link assistant.

As part of my workflow, I have access to:
1. A Neo4j knowledge graph database named "lilly_knowledge" with entities from your handwritten notes
2. Memory bank content with tool documentation and workflow examples
3. The ability to process handwritten notes using Claude's vision capabilities

To help you effectively, I can:
- Process handwritten notes from your reMarkable tablet
- Extract and organize knowledge from your notes
- Answer questions based on your handwritten content
- Help manage tasks and ideas found in your notes

Would you like me to:
- Process new handwritten notes?
- Explore your existing knowledge graph?
- Work with specific notebooks or ideas?
EOF

# Start Claude with Lilly's configuration
claude --instructions "$LILLY_INSTRUCTIONS" --dir "$WORKSPACE_DIR" --memory-bank-project "lilly"

echo
echo "Lilly session ended."