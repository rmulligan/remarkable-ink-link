#!/usr/bin/env python3
"""Demonstrate the enhanced Control Center state management capabilities."""

import asyncio
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

from inklink.control_center.state_manager import (  # noqa: E402
    ControlCenterState,
    StateEvent,
    StateEventType,
)
from inklink.control_center.core_enhanced import EnhancedInkControlCenter  # noqa: E402


class StateManagementDemo:
    """Demo of the enhanced state management system."""

    def __init__(self):
        self.state_file = "demo_state.json"
        self.state = ControlCenterState(persistence_path=self.state_file)
        self.event_log = []

    async def setup_event_handlers(self):
        """Set up event handlers to log state changes."""

        async def log_event(event: StateEvent):
            event_info = (
                f"[{event.timestamp.strftime('%H:%M:%S')}] {event.event_type.value}"
            )
            if event.zone_id:
                event_info += f" - Zone: {event.zone_id}"
            if event.data:
                event_info += f" - Data: {event.data}"
            self.event_log.append(event_info)
            print(event_info)

        # Register handlers for all event types
        for event_type in StateEventType:
            self.state.register_listener(event_type, log_event)

    async def demo_zone_management(self):
        """Demonstrate zone state management."""
        print("\n=== Zone Management Demo ===")

        # Create command zone
        await self.state.update_zone(
            "command_zone",
            {
                "active": True,
                "position": {"x": 100, "y": 100},
                "size": {"width": 300, "height": 200},
                "content": [],
            },
        )

        # Add content to zone
        await self.state.update_zone(
            "command_zone",
            {
                "active": True,
                "position": {"x": 100, "y": 100},
                "size": {"width": 300, "height": 200},
                "content": ["calendar", "todo", "notes"],
            },
        )

        # Create response zone
        await self.state.update_zone(
            "response_zone",
            {
                "active": True,
                "position": {"x": 500, "y": 100},
                "size": {"width": 400, "height": 300},
                "content": ["AI response will appear here"],
            },
        )

        # Display zones
        zones = await self.state.get_zones()
        print(f"\nActive zones: {list(zones.keys())}")

    async def demo_canvas_operations(self):
        """Demonstrate canvas state management."""
        print("\n=== Canvas Operations Demo ===")

        # Create main canvas
        await self.state.update_canvas(
            "main_canvas",
            {
                "width": 1920,
                "height": 1080,
                "active_tools": ["pen", "highlighter"],
                "layers": ["base", "annotations"],
                "zoom": 1.0,
            },
        )

        # Update canvas zoom
        await self.state.update_canvas(
            "main_canvas",
            {
                "width": 1920,
                "height": 1080,
                "active_tools": ["pen", "highlighter"],
                "layers": ["base", "annotations"],
                "zoom": 1.5,
            },
        )

        # Create secondary canvas
        await self.state.update_canvas(
            "scratch_canvas",
            {
                "width": 800,
                "height": 600,
                "active_tools": ["pencil"],
                "layers": ["scratch"],
                "zoom": 1.0,
            },
        )

        # Display canvases
        canvases = await self.state.get_canvases()
        print(f"\nActive canvases: {list(canvases.keys())}")

    async def demo_agent_lifecycle(self):
        """Demonstrate agent state tracking."""
        print("\n=== Agent Lifecycle Demo ===")

        # Start an agent
        agent_id = "handwriting_agent"
        await self.state.update_agent_state(
            agent_id,
            {
                "status": "starting",
                "task": "process_handwriting",
                "started_at": datetime.now().isoformat(),
            },
        )

        # Update to running
        await asyncio.sleep(0.5)
        await self.state.update_agent_state(
            agent_id,
            {
                "status": "running",
                "task": "process_handwriting",
                "progress": 50,
                "started_at": datetime.now().isoformat(),
            },
        )

        # Complete the agent task
        await asyncio.sleep(0.5)
        await self.state.update_agent_state(
            agent_id,
            {
                "status": "completed",
                "task": "process_handwriting",
                "result": "Text extracted: Hello World",
                "completed_at": datetime.now().isoformat(),
            },
        )

        # Display agent states
        agents = await self.state.get_agents()
        print(f"\nAgent states: {json.dumps(agents, indent=2)}")

    async def demo_task_management(self):
        """Demonstrate task state management."""
        print("\n=== Task Management Demo ===")

        # Create a task
        task_id = await self.state.add_task(
            "task_1",
            {
                "type": "handwriting_recognition",
                "priority": "high",
                "zone_id": "command_zone",
            },
        )

        # Update task status
        await self.state.update_task_status(task_id, "running")
        await asyncio.sleep(0.5)

        # Complete task
        await self.state.complete_task(
            task_id, {"result": "success", "output": "Recognized text: Hello World"}
        )

        # Create another task
        await self.state.add_task(
            "task_2",
            {"type": "ai_response", "priority": "medium", "depends_on": task_id},
        )

        # Display tasks
        tasks = await self.state.get_tasks()
        print(f"\nActive tasks: {len(tasks)}")
        for tid, task in tasks.items():
            print(f"  {tid}: {task['status']} - {task.get('type', 'unknown')}")

    async def demo_snapshot_and_recovery(self):
        """Demonstrate snapshot creation and state recovery."""
        print("\n=== Snapshot and Recovery Demo ===")

        # Create a snapshot
        snapshot = await self.state.create_snapshot()
        print(f"\nSnapshot created at: {snapshot.timestamp}")
        print(f"Version: {snapshot.version}")
        print(f"Zones: {len(snapshot.zones)}")
        print(f"Tasks: {len(snapshot.tasks)}")

        # Save state
        await self.state._save_state()
        print(f"\nState saved to {self.state_file}")

        # Create new state instance (simulating recovery)
        new_state = ControlCenterState(persistence_path=self.state_file)

        # Check recovered state
        recovered_zones = await new_state.get_zones()
        recovered_tasks = await new_state.get_tasks()

        print(f"\nRecovered state:")
        print(f"  Zones: {len(recovered_zones)}")
        print(f"  Tasks: {len(recovered_tasks)}")

    async def run_demo(self):
        """Run the complete demo."""
        print("=== Enhanced Control Center State Management Demo ===")

        # Set up event handlers
        await self.setup_event_handlers()

        # Run demo sections
        await self.demo_zone_management()
        await asyncio.sleep(1)

        await self.demo_canvas_operations()
        await asyncio.sleep(1)

        await self.demo_agent_lifecycle()
        await asyncio.sleep(1)

        await self.demo_task_management()
        await asyncio.sleep(1)

        await self.demo_snapshot_and_recovery()

        # Display event log
        print("\n=== Event Log ===")
        for event in self.event_log[-10:]:  # Show last 10 events
            print(event)

        print(f"\nTotal events logged: {len(self.event_log)}")

        # Cleanup
        if Path(self.state_file).exists():
            Path(self.state_file).unlink()
            print(f"\nCleaned up {self.state_file}")


async def main():
    """Run the state management demo."""
    demo = StateManagementDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
