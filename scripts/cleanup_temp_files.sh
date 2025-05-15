#!/bin/bash
# cleanup_temp_files.sh
# Script to safely clean up temporary files and directories

set -e  # Exit on error

# Print header
echo "=========================================================="
echo "          InkLink Temporary File Cleanup Script"
echo "=========================================================="
echo 

# Define directories to clean
TEMP_DIRS=(
    "temp"
    "temp_extract"
    "temp_files"
    "temp_container"
    "handwriting_model/docker_temp"
    "src/inklink/temp"
)

# Define patterns for backup files to remove
BACKUP_PATTERNS=(
    "*.bak"
    "*~"
    "*.swp"
)

# Define rendered output directories to clean
OUTPUT_DIRS=(
    "handwriting_model/rendered_pages"
    "handwriting_model/rmc_output"
    "handwriting_model/extracted"
    "handwriting_model/extracted_claude"
    "handwriting_model/latest_extract"
    "temp_extract/output"
    "temp_extract/output_page"
    "temp_extract/output_page_files"
    "temp_extract/cassidy_test_output"
)

# Function to safely clean a directory
clean_dir() {
    local dir="$1"
    if [ -d "$dir" ]; then
        echo "Cleaning directory: $dir"
        
        # Create a backup directory if it doesn't exist
        if [ ! -d "$dir/.backup" ]; then
            mkdir -p "$dir/.backup"
        fi
        
        # Move all files except .backup to the backup directory
        find "$dir" -maxdepth 1 -not -path "$dir" -not -path "$dir/.backup" -exec mv {} "$dir/.backup/" \;
        
        echo "✓ Done. Files moved to $dir/.backup/"
    else
        echo "Directory not found: $dir (skipping)"
    fi
}

# Function to remove backup files
remove_backups() {
    for pattern in "${BACKUP_PATTERNS[@]}"; do
        echo "Searching for backup files matching: $pattern"
        
        # Find and list backup files
        files=$(find . -type f -name "$pattern" 2>/dev/null || echo "")
        
        if [ -n "$files" ]; then
            echo "Found the following backup files:"
            echo "$files"
            echo "Removing backup files..."
            
            # Remove backup files
            find . -type f -name "$pattern" -delete 2>/dev/null
            
            echo "✓ Done"
        else
            echo "No files found matching pattern $pattern"
        fi
    done
}

# Main script execution
echo "Starting cleanup process..."
echo

echo "Step 1: Cleaning temporary directories"
for dir in "${TEMP_DIRS[@]}"; do
    clean_dir "$dir"
done
echo

echo "Step 2: Cleaning output directories"
for dir in "${OUTPUT_DIRS[@]}"; do
    clean_dir "$dir"
done
echo

echo "Step 3: Removing backup files"
remove_backups
echo

echo "Cleanup complete! 🎉"
echo
echo "Note: Original files have been moved to .backup directories"
echo "To permanently delete them, you can run: find . -name '.backup' -type d -exec rm -rf {} \\; 2>/dev/null || true"
echo

exit 0