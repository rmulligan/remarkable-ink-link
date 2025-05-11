#!/bin/bash

# Script to resolve conflicts in service files
# This script resolves conflicts in the service files by preferring the origin/main version

# Service files with conflicts
service_files=(
  "src/inklink/services/pdf_service.py"
  "src/inklink/services/qr_service.py"
  "src/inklink/services/remarkable_service.py"
  "src/inklink/services/web_scraper_service.py"
)

# Resolve conflicts by preferring origin/main
for file in "${service_files[@]}"; do
  echo "Resolving conflicts in $file"
  git checkout --theirs "$file"
  git add "$file"
done

echo "Service file conflicts resolved."