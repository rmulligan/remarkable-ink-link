#!/bin/bash
# Script to resolve conflicts by accepting incoming changes

# For each conflicted file
for file in src/inklink/adapters/handwriting_adapter.py src/inklink/services/handwriting_recognition_service.py tests/test_limitless_live.py; do
    echo "Processing $file"
    
    # Create a copy of the file
    cp "$file" "$file.backup"
    
    # Remove conflict markers and keep the incoming version (after =======)
    awk '
    BEGIN { in_conflict = 0; accept_incoming = 0 }
    /^<<<<<<</ { in_conflict = 1; next }
    /^=======/ { accept_incoming = 1; next }
    /^>>>>>>>/ { in_conflict = 0; accept_incoming = 0; next }
    { 
        if (!in_conflict || accept_incoming) print
    }' "$file.backup" > "$file"
    
    echo "Resolved $file"
done

echo "All conflicts resolved"