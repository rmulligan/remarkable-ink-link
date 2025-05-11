#!/bin/bash
# 
# Limitless Life Log Integration Demo Script
#
# This script runs a demonstration of the Limitless integration with InkLink.
# It sets up the necessary environment variables and starts the server with
# Limitless integration enabled.
#
# Usage:
#   ./scripts/run_limitless_demo.sh [api_key]
#
# If no API key is provided as an argument, it will use the one in the 
# LIMITLESS_API_KEY environment variable or prompt for one.
#

set -e

# Bold and color text
bold=$(tput bold)
green=$(tput setaf 2)
yellow=$(tput setaf 3)
blue=$(tput setaf 4)
reset=$(tput sgr0)

echo "${bold}${blue}╔════════════════════════════════════════════════════════════╗${reset}"
echo "${bold}${blue}║               InkLink Limitless Integration Demo            ║${reset}"
echo "${bold}${blue}╚════════════════════════════════════════════════════════════╝${reset}"
echo ""

# Check for API key in argument or environment
API_KEY=$1
if [ -z "$API_KEY" ]; then
  API_KEY=$LIMITLESS_API_KEY
fi

# Prompt for API key if not provided
if [ -z "$API_KEY" ]; then
  echo "${yellow}Limitless API key not found.${reset}"
  read -p "Please enter your Limitless API key: " API_KEY
  
  if [ -z "$API_KEY" ]; then
    echo "${bold}No API key provided. Exiting.${reset}"
    exit 1
  fi
fi

# Set up environment variables
export LIMITLESS_API_KEY=$API_KEY
export LIMITLESS_SYNC_INTERVAL=900  # 15 minutes for demo
export LIMITLESS_AUTOSTART=true
export NEO4J_URI=${NEO4J_URI:-"bolt://localhost:7687"}
export NEO4J_USER=${NEO4J_USER:-"neo4j"}
export NEO4J_PASS=${NEO4J_PASS:-"password"}

echo "${bold}Configuration:${reset}"
echo "• Limitless API Key: ${API_KEY:0:4}...${API_KEY: -4}"
echo "• Sync Interval: ${LIMITLESS_SYNC_INTERVAL} seconds"
echo "• Neo4j URI: ${NEO4J_URI}"
echo "• Limitless Autostart: ${LIMITLESS_AUTOSTART}"
echo ""

# Check Docker availability
if ! command -v docker &> /dev/null; then
  echo "${yellow}Docker not found. Running in local mode.${reset}"
  USE_DOCKER=false
else
  echo "${green}Docker found. Running in container mode.${reset}"
  USE_DOCKER=true
fi

# Function to run a curl request and print the result
function run_curl() {
  local url=$1
  local method=${2:-GET}
  local data=$3
  
  echo "${bold}${blue}→ ${method} ${url}${reset}"
  
  if [ "$method" = "GET" ]; then
    result=$(curl -s -X ${method} http://localhost:9999${url})
  else
    result=$(curl -s -X ${method} http://localhost:9999${url} -H "Content-Type: application/json" -d "${data}")
  fi
  
  # Format result if it's valid JSON
  if echo "$result" | jq '.' &> /dev/null; then
    echo "$(echo $result | jq '.')"
  else
    echo "$result"
  fi
  
  echo ""
}

# Check if server is already running
if curl -s http://localhost:9999/health &> /dev/null; then
  echo "${green}Server is already running on port 9999.${reset}"
else
  echo "${yellow}Starting InkLink server...${reset}"
  
  if [ "$USE_DOCKER" = true ]; then
    # Run with Docker
    docker-compose up -d inklink
  else
    # Run locally
    yarn start &
    SERVER_PID=$!
    
    # Wait for server to start
    echo "Waiting for server to start..."
    tries=0
    while [ $tries -lt 30 ]; do
      if curl -s http://localhost:9999/health &> /dev/null; then
        break
      fi
      sleep 1
      tries=$((tries+1))
    done
    
    if [ $tries -eq 30 ]; then
      echo "${bold}Server failed to start within 30 seconds. Exiting.${reset}"
      kill $SERVER_PID
      exit 1
    fi
  fi
  
  echo "${green}Server started successfully on port 9999.${reset}"
fi

echo ""
echo "${bold}${blue}╔════════════════════════════════════════════════════════════╗${reset}"
echo "${bold}${blue}║                  Limitless API Demonstration                ║${reset}"
echo "${bold}${blue}╚════════════════════════════════════════════════════════════╝${reset}"
echo ""

# Get status
echo "${bold}1. Checking Limitless integration status:${reset}"
run_curl "/limitless/status"

# Wait for the first sync
echo "${bold}2. Waiting for initial sync...${reset}"
sleep 5

# Get scheduler status
echo "${bold}3. Checking scheduler status:${reset}"
run_curl "/limitless/scheduler"

# Force sync all logs
echo "${bold}4. Triggering a full sync of all logs:${reset}"
run_curl "/limitless/sync" "POST" '{"force_full_sync": true}'

# Wait for sync to complete
echo "${bold}5. Waiting for sync to complete...${reset}"
sleep 5

# Get status after sync
echo "${bold}6. Checking status after sync:${reset}"
run_curl "/limitless/status"

# Get recent life logs (first need to get a log ID)
echo "${bold}7. Fetching a life log ID:${reset}"
status_response=$(curl -s http://localhost:9999/limitless/status)
log_count=$(echo "$status_response" | jq -r '.service.cached_log_count')

if [ "$log_count" -gt 0 ]; then
  # Get life logs from API directly
  echo "${yellow}Getting a life log ID from Limitless API...${reset}"
  logs_response=$(curl -s -H "X-API-Key: $API_KEY" "https://api.limitless.ai/v1/lifelogs?limit=1")
  log_id=$(echo "$logs_response" | jq -r '.data[0].id')
  
  if [ "$log_id" != "null" ] && [ -n "$log_id" ]; then
    echo "${green}Found log ID: $log_id${reset}"
    
    # Fetch the specific log
    echo "${bold}8. Fetching a specific life log:${reset}"
    run_curl "/limitless/logs/$log_id"
  else
    echo "${yellow}Could not find a log ID. Skipping log fetching.${reset}"
  fi
else
  echo "${yellow}No logs found in cache. Skipping log fetching.${reset}"
fi

# Stop scheduler
echo "${bold}9. Stopping the scheduler:${reset}"
run_curl "/limitless/scheduler?action=stop" "POST"

# Check scheduler status
echo "${bold}10. Checking scheduler status after stopping:${reset}"
run_curl "/limitless/scheduler"

# Start scheduler
echo "${bold}11. Starting the scheduler:${reset}"
run_curl "/limitless/scheduler?action=start" "POST"

# Check scheduler status
echo "${bold}12. Checking scheduler status after starting:${reset}"
run_curl "/limitless/scheduler"

# Demo completed
echo ""
echo "${bold}${green}╔════════════════════════════════════════════════════════════╗${reset}"
echo "${bold}${green}║                 Demo completed successfully!                ║${reset}"
echo "${bold}${green}╚════════════════════════════════════════════════════════════╝${reset}"
echo ""
echo "The server is still running. You can access the API at http://localhost:9999"
echo ""
echo "Available endpoints:"
echo "• GET  /limitless/status - Get current status"
echo "• GET  /limitless/scheduler - Get scheduler status"
echo "• POST /limitless/scheduler?action=start - Start scheduler"
echo "• POST /limitless/scheduler?action=stop - Stop scheduler"
echo "• POST /limitless/sync - Trigger a sync"
echo "• POST /limitless/sync?force=true - Trigger a full sync"
echo "• GET  /limitless/logs/{log_id} - Get a specific log"
echo "• DELETE /limitless/cache - Clear log cache"
echo ""
echo "To stop the server:"
echo "• Docker: yarn docker:down"
echo "• Local: kill $(pgrep -f 'python.*main.py')"
echo ""

if [ "$USE_DOCKER" = false ] && [ -n "$SERVER_PID" ]; then
  echo "Press Ctrl+C to stop the server and exit."
  wait $SERVER_PID
fi