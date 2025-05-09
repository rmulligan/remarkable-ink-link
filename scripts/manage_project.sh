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
if PROJECT_INFO=$(gh project list --owner "$OWNER" --format json | jq -r --arg name "$PROJECT_NAME" '.projects[] | select(.title==$name)'); then
  PROJECT_NUMBER=$(echo "$PROJECT_INFO" | jq -r '.number')
  if [[ -n "$PROJECT_NUMBER" ]]; then
    echo "Project '$PROJECT_NAME' already exists (number $PROJECT_NUMBER)"
  else
    echo "Project not found; creating project '$PROJECT_NAME'..."
    # Create a new project 
    PROJECT_INFO=$(gh project create --owner "$OWNER" --title "$PROJECT_NAME" --format json)
    PROJECT_NUMBER=$(echo "$PROJECT_INFO" | jq -r '.number')
    echo "Created project '$PROJECT_NAME' (number $PROJECT_NUMBER)"
    
    # Add default fields and views if project was just created
    echo "Setting up default fields and views..."
    gh project field-create --owner "$OWNER" --project-number "$PROJECT_NUMBER" --name "Status" --data-type "SingleSelect" --single-select-options "Todo,In Progress,Done"
    gh project field-create --owner "$OWNER" --project-number "$PROJECT_NUMBER" --name "Priority" --data-type "SingleSelect" --single-select-options "High,Medium,Low"
  fi
else
  echo "Failed to query projects or project not found"
  exit 1
fi

echo "Project maintenance complete: '$PROJECT_NAME' is project number $PROJECT_NUMBER"