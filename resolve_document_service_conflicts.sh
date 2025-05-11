#!/bin/bash

# Script to resolve document_service.py and interfaces.py conflicts

# Fix document_service.py
echo "Resolving document_service.py conflicts"
# Replace the specific line with the next() implementation
sed -i 's/        for converter in self.converters:/        return next(\n            (\n                converter\n                for converter in self.converters\n                if converter.can_convert(content_type)\n            ),\n            None,\n        )/' src/inklink/services/document_service.py

# Update the create_hcl method call to include config parameter
sed -i 's/        return create_hcl_from_content(url, qr_path, content, self.temp_dir)/        return create_hcl_from_content(url, qr_path, content, self.temp_dir, None)/' src/inklink/services/document_service.py

# Fix interfaces.py
echo "Resolving interfaces.py conflicts"
# Use git checkout --theirs to accept origin/main version first
git checkout --theirs src/inklink/services/interfaces.py

# Git add the files
git add src/inklink/services/document_service.py
git add src/inklink/services/interfaces.py

echo "Document service and interfaces conflicts resolved."