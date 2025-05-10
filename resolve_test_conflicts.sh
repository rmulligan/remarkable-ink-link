#!/bin/bash

# Script to resolve conflicts in test files
# This script resolves conflicts in test files by preferring the origin/main version

# Test files with conflicts
test_files=(
  "tests/test_document_service.py"
  "tests/test_full_roundtrip.py"
  "tests/test_google_docs_service.py"
  "tests/test_handwriting_recognition.py"
  "tests/test_html_utils.py"
  "tests/test_pdf_service.py"
  "tests/test_qr_service.py"
  "tests/test_rcu.py"
  "tests/test_remarkable_service.py"
  "tests/test_server.py"
  "tests/test_web_scraper_service.py"
  "tests/test_web_ui_endpoints.py"
  "tests/test_hcl_render.py"
)

# Resolve conflicts by preferring origin/main
for file in "${test_files[@]}"; do
  echo "Resolving conflicts in $file"
  if [[ -f "$file" ]]; then
    # Use git checkout --theirs to choose the origin/main version
    git checkout --theirs "$file"
    # Mark as resolved
    git add "$file"
  else
    echo "Skipping missing file: $file"
  fi
done

echo "Test file conflicts resolved."