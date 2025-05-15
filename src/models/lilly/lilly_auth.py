#!/usr/bin/env python3
"""
Lilly Authentication CLI.

This script provides a command-line interface for authenticating Lilly
with various services including Proton Mail, Proton Calendar, and Google Drive.
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from lilly.auth.cli import auth  # noqa: E402

if __name__ == "__main__":
    auth()
