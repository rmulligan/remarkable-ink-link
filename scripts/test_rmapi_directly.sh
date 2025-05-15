#!/bin/bash
# Direct test of rmapi without Python wrapper

echo "Testing rmapi directly..."

# Set the path to rmapi
RMAPI="/home/ryan/dev/remarkable-ink-link/local-rmapi"

# Test listing files
echo "=== Testing ls ==="
$RMAPI ls

# Test downloading a specific file - try with a different notebook
echo "=== Testing get on 'Testing Notebook' ==="
cd /tmp
$RMAPI get "Testing Notebook"
ls -la

# Test downloading with verbose flag if available
echo "=== Testing get with verbose ==="
$RMAPI -v get "Testing Notebook"

# Test creating and uploading a simple text file
echo "=== Testing put with text file ==="
echo "Hello from test" > test_upload.txt
$RMAPI put test_upload.txt

# Clean up
rm -f test_upload.txt

echo "Test complete."