#!/bin/bash

# Resolve mock_handwriting_adapter in function arguments
sed -i 's/\(handwriting_adapter=mock_handwriting_adapter\)\s*$\(>>>>>>> Stashed changes\)/\1,/g' /home/ryan/dev/remarkable-ink-link/tests/test_handwriting_recognition.py

# Fix conflict markers and prefer the upstream formatting with commas and newlines
sed -i 's/<<<<<<< Updated upstream\s*\(.*\)\s*=======\s*\(.*\)\s*>>>>>>> Stashed changes/\1/g' /home/ryan/dev/remarkable-ink-link/tests/test_handwriting_recognition.py

# Replace any remaining conflict markers
sed -i '/<<<<<<< Updated upstream/d' /home/ryan/dev/remarkable-ink-link/tests/test_handwriting_recognition.py
sed -i '/=======$/d' /home/ryan/dev/remarkable-ink-link/tests/test_handwriting_recognition.py
sed -i '/>>>>>>> Stashed changes/d' /home/ryan/dev/remarkable-ink-link/tests/test_handwriting_recognition.py