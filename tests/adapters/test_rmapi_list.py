#!/usr/bin/env python
import logging
import sys
from src.inklink.adapters.rmapi_adapter import RmapiAdapter

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)

# Initialize adapter with the path to rmapi
adapter = RmapiAdapter("/home/ryan/bin/rmapi")

# Test ping to check basic connectivity
print("Testing connectivity...")
connected = adapter.ping()
print(f"Connected: {connected}")

# Call list_files method and see what happens
print("\nTesting list_files method...")
success, documents = adapter.list_files()
print(f"Success: {success}")
print(f"Found {len(documents)} documents")

# Debug output for each document
for i, doc in enumerate(documents):
    print(f"Document {i+1}:")
    print(f"  ID: {doc.get('ID', 'N/A')}")
    print(f"  Name: {doc.get('VissibleName', 'N/A')}")
    print(f"  Type: {doc.get('Type', 'N/A')}")
    print()

print("Test complete.")