#!/usr/bin/env bash
#
# scripts/manage_project.sh
# Utility to create or update the "InkLink Kanban" GitHub Project board using gh + gh-project extension.

set -euo pipefail

# Configuration
REPO="rmulligan/remarkable-ink-link"
PROJECT_NAME="InkLink Kanban"

# Ensure gh-project extension is installed
if ! gh extension list | grep -q 'github/gh-projects'; then
  echo "Installing gh-projects extension..."
  gh extension install github/gh-projects
fi

echo "Looking for project '$PROJECT_NAME' in repo '$REPO'..."
# Query project list and extract its number if exists
PROJECT_NUMBER=$(gh projects list --repo "$REPO" --json number,name --jq '.[] | select(.name=="'"$PROJECT_NAME"'").number')

if [[ -z "$PROJECT_NUMBER" ]]; then
  echo "Project not found; creating project '$PROJECT_NAME'..."
  gh projects create "$PROJECT_NAME" --repo "$REPO" --description "Kanban board for InkLink tasks"
  # re-query the project number
  PROJECT_NUMBER=$(gh projects list --repo "$REPO" --json number,name --jq '.[] | select(.name=="'"$PROJECT_NAME"'").number')
  echo "Created project '$PROJECT_NAME' (number $PROJECT_NUMBER)"
else
  echo "Project '$PROJECT_NAME' already exists (number $PROJECT_NUMBER)"
fi

echo "Project maintenance complete: '$PROJECT_NAME' is project number $PROJECT_NUMBER"