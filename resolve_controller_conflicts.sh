#!/bin/bash

# Script to resolve controller conflicts automatically
# This script resolves conflicts in the controller files by preferring the origin/main version

# Controller files
controller_files=(
  "src/inklink/controllers/__init__.py"
  "src/inklink/controllers/auth_controller.py"
  "src/inklink/controllers/base_controller.py"
  "src/inklink/controllers/download_controller.py"
  "src/inklink/controllers/ingest_controller.py"
  "src/inklink/controllers/process_controller.py"
  "src/inklink/controllers/response_controller.py"
  "src/inklink/controllers/share_controller.py"
  "src/inklink/controllers/upload_controller.py"
)

# Resolve conflicts by preferring origin/main
for file in "${controller_files[@]}"; do
  echo "Resolving conflicts in $file"
  # Use git checkout --theirs to choose the origin/main version
  git checkout --theirs "$file"
  # Mark as resolved
  git add "$file"
done

echo "Controller conflicts resolved. Check the files to make sure everything looks correct."