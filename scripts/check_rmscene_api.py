#!/usr/bin/env python3
"""Check rmscene API to understand the correct usage."""

import inspect

import rmscene
import rmscene.scene_tree as st
from rmscene.scene_stream import SceneTree, read_tree, write_blocks

print("=== read_tree signature ===")
print(inspect.signature(read_tree))
print()

print("=== write_blocks signature ===")
print(inspect.signature(write_blocks))
print()

print("=== SceneTree methods ===")
for name, method in inspect.getmembers(SceneTree):
    if not name.startswith("_") and callable(method):
        try:
            sig = inspect.signature(method)
            print(f"{name}: {sig}")
        except Exception:
            print(f"{name}: (no signature)")
print()

# Check how to save a scene tree
print("=== Looking for write/save methods ===")

for name in dir(st):
    if "write" in name.lower() or "save" in name.lower():
        print(f"Found: {name}")

# Check the main module
print("\n=== Main rmscene module ===")

for name in dir(rmscene):
    if "write" in name.lower() or "save" in name.lower():
        print(f"Found: {name}")
