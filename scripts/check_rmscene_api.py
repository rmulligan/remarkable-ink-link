#!/usr/bin/env python3
"""Check rmscene API to understand the correct usage."""

import inspect
from rmscene.scene_stream import read_tree, write_blocks, SceneTree

print("=== read_tree signature ===")
print(inspect.signature(read_tree))
print()

print("=== write_blocks signature ===")
print(inspect.signature(write_blocks))
print()

print("=== SceneTree methods ===")
for name, method in inspect.getmembers(SceneTree):
    if not name.startswith('_') and callable(method):
        try:
            sig = inspect.signature(method)
            print(f"{name}: {sig}")
        except:
            print(f"{name}: (no signature)")
print()

# Check how to save a scene tree
print("=== Looking for write/save methods ===")
import rmscene.scene_tree as st
for name in dir(st):
    if 'write' in name.lower() or 'save' in name.lower():
        print(f"Found: {name}")
        
# Check the main module
print("\n=== Main rmscene module ===")
import rmscene
for name in dir(rmscene):
    if 'write' in name.lower() or 'save' in name.lower():
        print(f"Found: {name}")