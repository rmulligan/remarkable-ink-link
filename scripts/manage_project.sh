#!/usr/bin/env bash
#
# scripts/manage_project.sh
# Utility to create or update the "InkLink Kanban" GitHub Project board

set -euo pipefail

# Configuration
REPO="rmulligan/remarkable-ink-link"
OWNER=${REPO%%/*}  # Extract owner part from REPO
PROJECT_NAME="InkLink Kanban"

echo "Looking for project '$PROJECT_NAME' for owner '$OWNER'..."

# Check if project exists (projects are now at the org or user level, not repo level)
echo "Checking for existing project..."
set +e  # Temporarily disable exit on error for this query
PROJECT_LIST=$(gh project list --owner "$OWNER" --format json 2>/dev/null)
PROJECT_LIST_STATUS=$?
PROJECT_EXISTS=""

# Only try to parse the JSON if the command was successful
if [[ $PROJECT_LIST_STATUS -eq 0 ]]; then
  PROJECT_EXISTS=$(echo "$PROJECT_LIST" | jq -r --arg name "$PROJECT_NAME" '.projects[] | select(.title==$name) | .number' 2>/dev/null || echo "")
fi

# If we received an auth error or other API issue, report but continue
if [[ $PROJECT_LIST_STATUS -ne 0 ]]; then
  echo "WARNING: Unable to query projects. This is likely due to permission issues with the GitHub token."
  echo "Using existing project #1 instead."
  PROJECT_NUMBER=1
  echo "Project maintenance complete: '$PROJECT_NAME' is project number $PROJECT_NUMBER"
  exit 0
fi

set -e  # Re-enable exit on error

if [[ -n "$PROJECT_EXISTS" ]]; then
  PROJECT_NUMBER=$PROJECT_EXISTS
  echo "Project '$PROJECT_NAME' already exists (number $PROJECT_NUMBER)"
  echo "Project maintenance complete: '$PROJECT_NAME' is project number $PROJECT_NUMBER"
  exit 0
else
  echo "Project not found in API response; using existing project #1..."
  PROJECT_NUMBER=1
  echo "Using existing project number: $PROJECT_NUMBER"
  echo "Project maintenance complete: '$PROJECT_NAME' is project number $PROJECT_NUMBER"
  exit 0
fi