#!/usr/bin/env python3
"""Migrate from the basic Control Center to the enhanced version with state management."""

import json
import os
import shutil
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.inklink.control_center.core import InkControlCenter  # noqa: E402
from src.inklink.control_center.core_enhanced import (  # noqa: E402
    EnhancedInkControlCenter,
)


def backup_original_file(file_path: Path):
    """Create a backup of the original file."""
    backup_path = file_path.with_suffix(".py.bak")
    if file_path.exists():
        shutil.copy2(file_path, backup_path)
        print(f"Backed up {file_path} to {backup_path}")


def update_imports(content: str) -> str:
    """Update import statements in the given content."""
    # Replace the old import with the new one
    old_import = "from inklink.control_center.core import InkControlCenter"
    new_import = "from inklink.control_center.core_enhanced import EnhancedInkControlCenter as InkControlCenter"

    content = content.replace(old_import, new_import)

    # Also handle relative imports
    old_relative = "from .core import InkControlCenter"
    new_relative = (
        "from .core_enhanced import EnhancedInkControlCenter as InkControlCenter"
    )

    content = content.replace(old_relative, new_relative)

    return content


def migrate_control_center():
    """Migrate the Control Center to use the enhanced version."""
    print("Starting Control Center migration...")

    # Define paths
    project_root = Path(__file__).parent.parent
    control_center_dir = project_root / "src" / "inklink" / "control_center"

    # Backup the original core.py
    original_core = control_center_dir / "core.py"
    backup_original_file(original_core)

    # Update __init__.py to export the enhanced version
    init_file = control_center_dir / "__init__.py"
    if init_file.exists():
        backup_original_file(init_file)

        with open(init_file, "r") as f:
            content = f.read()

        # Update the import
        content = update_imports(content)

        # Add state manager to exports
        if "from .state_manager import" not in content:
            content += "\nfrom .state_manager import ControlCenterState, StateEvent, StateEventType\n"

        with open(init_file, "w") as f:
            f.write(content)

        print(f"Updated {init_file}")

    # Update any files that import the control center
    files_to_update = [
        "src/inklink/server.py",
        "src/inklink/controllers/process_controller.py",
        "src/inklink/controllers/base_controller.py",
        "src/inklink/main.py",
    ]

    for file_path in files_to_update:
        full_path = project_root / file_path
        if full_path.exists():
            backup_original_file(full_path)

            with open(full_path, "r") as f:
                content = f.read()

            # Update imports
            updated_content = update_imports(content)

            # Update initialization calls to include state_file parameter
            if "InkControlCenter(" in updated_content:
                # Add state file parameter if not present
                updated_content = updated_content.replace(
                    "InkControlCenter(",
                    "InkControlCenter(state_file='control_center_state.json', ",
                )

            if content != updated_content:
                with open(full_path, "w") as f:
                    f.write(updated_content)
                print(f"Updated {full_path}")

    # Create a default state file if it doesn't exist
    state_file = project_root / "control_center_state.json"
    if not state_file.exists():
        default_state = {
            "zones": {},
            "canvases": {},
            "agents": {},
            "tasks": {},
            "settings": {"auto_save": True, "save_interval": 300},
            "version": 1,
        }

        with open(state_file, "w") as f:
            json.dump(default_state, f, indent=2)

        print(f"Created default state file at {state_file}")

    print("\nMigration completed successfully!")
    print("The following changes were made:")
    print("1. Backed up original files")
    print("2. Updated imports to use the enhanced Control Center")
    print("3. Added state file parameter to initialization calls")
    print("4. Created default state file")
    print("\nTo revert the changes, restore the .bak files")


if __name__ == "__main__":
    migrate_control_center()
