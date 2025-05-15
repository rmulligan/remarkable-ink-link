#!/usr/bin/env python3
import os
import sys

print("Python executable:", sys.executable)
print("LIMITLESS_API_KEY:", os.environ.get("LIMITLESS_API_KEY", "Not found"))
print("NEO4J_URI:", os.environ.get("NEO4J_URI", "Not found"))
print("VIRTUAL_ENV:", os.environ.get("VIRTUAL_ENV", "Not found"))