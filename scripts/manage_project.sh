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
PROJECT_EXISTS=$(echo "$PROJECT_LIST" | jq -r --arg name "$PROJECT_NAME" '.projects[] | select(.title==$name) | .number')
set -e  # Re-enable exit on error

if [[ -n "$PROJECT_EXISTS" ]]; then
  PROJECT_NUMBER=$PROJECT_EXISTS
  echo "Project '$PROJECT_NAME' already exists (number $PROJECT_NUMBER)"
else
  echo "Project not found; creating project '$PROJECT_NAME'..."
  # Create a new project 
  set +e  # Temporarily disable exit on error for project creation
  PROJECT_INFO=$(gh project create --owner "$OWNER" --title "$PROJECT_NAME" --format json 2>/dev/null)
  CREATE_STATUS=$?
  set -e  # Re-enable exit on error
  
  if [[ $CREATE_STATUS -eq 0 ]]; then
    PROJECT_NUMBER=$(echo "$PROJECT_INFO" | jq -r '.number')
    echo "Created project '$PROJECT_NAME' (number $PROJECT_NUMBER)"
    
    # Add default fields and views if project was just created
    echo "Setting up default fields and views..."
    gh project field-create --owner "$OWNER" --project-number "$PROJECT_NUMBER" --name "Status" --data-type "SingleSelect" --single-select-options "Todo,In Progress,Done"
    gh project field-create --owner "$OWNER" --project-number "$PROJECT_NUMBER" --name "Priority" --data-type "SingleSelect" --single-select-options "High,Medium,Low"
  else
    echo "NOTE: Unable to create project automatically."
    echo "This is usually due to permission issues with the GitHub token."
    echo "Please create the project manually in GitHub and then run this script again."
    echo "Manual creation URL: https://github.com/users/$OWNER/projects"
    
    # Ask for manual input
    echo "If you've already created the project, enter its number now or press Enter to exit:"
    read -r MANUAL_PROJECT_NUMBER
    if [[ -n "$MANUAL_PROJECT_NUMBER" ]]; then
      PROJECT_NUMBER=$MANUAL_PROJECT_NUMBER
      echo "Using manual project number: $PROJECT_NUMBER"
    else
      echo "Exiting without project configuration."
      exit 1
    fi
  fi
fi

echo "Project maintenance complete: '$PROJECT_NAME' is project number $PROJECT_NUMBER"