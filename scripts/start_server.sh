
#!/usr/bin/env bash

# Server startup script for testing
# Starts the InkLink server in the background and waits for it to be ready

# Default port (can be overridden with PORT environment variable)
PORT=${PORT:-9999}
HOST=${HOST:-"127.0.0.1"}
MAX_WAIT_TIME=30  # Maximum time to wait for server in seconds

# Create a temporary directory for mock scripts
TEMP_DIR=$(mktemp -d)
MOCK_RMAPI="${TEMP_DIR}/rmapi"

# Create a mock rmapi script that always returns success
cat > "${MOCK_RMAPI}" << 'EOF'
#!/usr/bin/env bash
# Mock rmapi script that always returns success
# It handles the 'ls' command used in the authentication check

if [[ "$1" == "ls" ]]; then
  echo "/"
  exit 0
fi

# For 'put' command, simulate successful upload
if [[ "$1" == "put" ]]; then
  echo "Upload successful"
  echo "Document ID: mock-doc-123456"
  exit 0
fi

# Default success
exit 0
EOF

# Make the mock script executable
chmod +x "${MOCK_RMAPI}"

# Function to check if a port is already in use
is_port_in_use() {
  nc -z "$HOST" "$PORT" >/dev/null 2>&1
  return $?
}

# Function to find an available port
find_available_port() {
  local original_port=$PORT
  local max_attempts=10
  local attempts=0
  
  while is_port_in_use && [ $attempts -lt $max_attempts ]; do
    PORT=$((PORT + 1))
    attempts=$((attempts + 1))
  done
  
  if is_port_in_use; then
    echo "Error: Could not find an available port after $max_attempts attempts starting from $original_port" >&2
    return 1
  fi
  
  return 0
}

# Function to check if the server is ready
check_server_ready() {
  # Try to connect to the server with POST method
  if curl -s -X POST -H "Content-Type: application/json" -d '{"url":"http://example.com"}' "http://$HOST:$PORT/share" -o /dev/null; then
    return 0
  else
    return 1
  fi
}

# Function to wait for the server to be ready
wait_for_server() {
  local elapsed=0
  local interval=1
  local max_retries=3
  local retry_count=0
  
  echo "Waiting for server to be ready on $HOST:$PORT..."
  
  while [ $elapsed -lt $MAX_WAIT_TIME ]; do
    if check_server_ready; then
      echo "Server is ready on $HOST:$PORT"
      return 0
    fi
    
    # Check if the server process is still running
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      echo "Error: Server process (PID: $SERVER_PID) has terminated unexpectedly" >&2
      return 1
    fi
    
    # Retry with increasing backoff
    sleep $interval
    elapsed=$((elapsed + interval))
    
    # Increase interval slightly for exponential backoff
    if [ $((elapsed % 5)) -eq 0 ]; then
      interval=$((interval + 1))
    fi
    
    echo -n "."
  done
  
  echo
  echo "Error: Server did not become ready within $MAX_WAIT_TIME seconds" >&2
  echo "Checking server logs for errors..."
  
  # Try to get some diagnostic information
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Server process is still running. It might be waiting for additional resources or stuck."
  else
    echo "Server process has terminated."
  fi
  
  return 1
}

# Function to clean up when the script exits
cleanup() {
  if [ -n "$SERVER_PID" ]; then
    echo "Stopping server (PID: $SERVER_PID)..."
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  
  # Remove the temporary directory with mock scripts
  if [ -d "$TEMP_DIR" ]; then
    echo "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
  fi
}

# Set up trap to clean up on exit
trap cleanup EXIT INT TERM

# Check if python is available
if ! command -v python3 &>/dev/null; then
  echo "Error: python3 is required but not found" >&2
  exit 1
fi

# Find an available port
if ! find_available_port; then
  exit 1
fi

# Start the server in the background

echo "Starting InkLink server on $HOST:$PORT..."
echo "Using mock rmapi at $MOCK_RMAPI for authentication bypass"
INKLINK_RMAPI="$MOCK_RMAPI" python3 -m inklink.main server --host "$HOST" --port "$PORT" &
SERVER_PID=$!
    

# Check if the server process is still running after a short delay
sleep 1
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "Error: Server failed to start" >&2
  exit 1
fi

# Wait for the server to be ready
if ! wait_for_server; then
  echo "Error: Server did not become ready in time" >&2
  exit 1
fi

# Output the server information for other scripts to use
# Output and export the server information for other scripts to use
export SERVER_PID=$SERVER_PID
export SERVER_PORT=$PORT
export SERVER_HOST=$HOST
echo "SERVER_PID=$SERVER_PID"
echo "SERVER_PORT=$PORT"
echo "SERVER_HOST=$HOST"
