"""Demo of the InkLink Control Center."""

import asyncio
import logging
from pathlib import Path

from inklink.adapters.handwriting_adapter import HandwritingAdapter
from inklink.adapters.remarkable_adapter import RemarkableAdapter
from inklink.agents.base.agent import AgentConfig
from inklink.agents.core.control_center_agent import ControlCenterAgent
from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)
from inklink.services.remarkable_service import RemarkableService


async def simulate_ink_interaction(control_center_agent):
    """Simulate various ink interactions with the control center."""

    # Simulate creating a task
    print("\n1. Creating a task with handwriting...")
    task_strokes = [
        {
            "points": [(100, 50), (120, 50), (140, 50)],  # Simple line
            "pressure": [1.0, 1.0, 1.0],
            "timestamp": 1234567890,
        }
    ]

    result = await control_center_agent.handle_request(
        {"type": "process_ink", "data": {"strokes": task_strokes, "zone_id": "kanban"}}
    )
    print(f"Result: {result}")

    # Simulate drawing an arrow (task assignment)
    print("\n2. Assigning task to agent with arrow gesture...")
    arrow_strokes = [
        {
            "points": [(150, 100), (200, 100), (250, 100), (240, 90), (240, 110)],
            "pressure": [1.0] * 5,
            "timestamp": 1234567891,
        }
    ]

    result = await control_center_agent.handle_request(
        {"type": "process_ink", "data": {"strokes": arrow_strokes, "zone_id": "kanban"}}
    )
    print(f"Result: {result}")

    # Simulate agent command
    print("\n3. Writing agent command...")
    command_strokes = [
        {
            "points": [(50, 200), (60, 200), (70, 200)],  # @Agent[Limitless]: analyze
            "pressure": [1.0, 1.0, 1.0],
            "timestamp": 1234567892,
        }
    ]

    result = await control_center_agent.handle_request(
        {
            "type": "process_ink",
            "data": {"strokes": command_strokes, "zone_id": "discussion"},
        }
    )
    print(f"Result: {result}")

    # Simulate quick action tap
    print("\n4. Tapping sync button...")
    tap_strokes = [
        {
            "points": [(400, 550)],  # Single point tap
            "pressure": [1.0],
            "timestamp": 1234567893,
        }
    ]

    result = await control_center_agent.handle_request(
        {"type": "process_ink", "data": {"strokes": tap_strokes, "zone_id": "actions"}}
    )
    print(f"Result: {result}")

    # Simulate circle gesture (selection)
    print("\n5. Selecting item with circle gesture...")
    circle_strokes = [
        {
            "points": [
                (100, 100),
                (110, 90),
                (120, 85),
                (130, 85),
                (140, 90),
                (145, 100),
                (145, 110),
                (140, 120),
                (130, 125),
                (120, 125),
                (110, 120),
                (105, 110),
                (100, 100),  # Back to start
            ],
            "pressure": [1.0] * 13,
            "timestamp": 1234567894,
        }
    ]

    result = await control_center_agent.handle_request(
        {
            "type": "process_ink",
            "data": {"strokes": circle_strokes, "zone_id": "kanban"},
        }
    )
    print(f"Result: {result}")


async def demo_control_center_visualization(control_center_agent):
    """Demo visualization capabilities."""

    print("\n=== Control Center Visualization Demo ===")

    # Generate the notebook
    print("\n1. Generating control center notebook...")
    result = await control_center_agent.handle_request(
        {"type": "create_control_center"}
    )
    print(f"Created notebook: {result.get('notebook_id')}")

    # Update display with sample data
    print("\n2. Updating display with sample data...")

    # Update agent status
    await control_center_agent.handle_request(
        {
            "type": "update_display",
            "data": {
                "zone_id": "agents",
                "update_type": "set_data",
                "data": {
                    "agents": {
                        "Limitless": {
                            "status": "running",
                            "last_action": "Processed 10 transcripts",
                        },
                        "Briefing": {
                            "status": "idle",
                            "last_action": "Generated morning brief",
                        },
                        "Tracker": {
                            "status": "processing",
                            "current_task": "Updating project statuses",
                        },
                    }
                },
            },
        }
    )

    # Update kanban board
    await control_center_agent.handle_request(
        {
            "type": "update_display",
            "data": {
                "zone_id": "kanban",
                "update_type": "set_data",
                "data": {
                    "tasks": [
                        {
                            "id": "1",
                            "title": "Fix MCP integration",
                            "status": "todo",
                            "tags": ["urgent"],
                        },
                        {"id": "2", "title": "Update documentation", "status": "doing"},
                        {"id": "3", "title": "Deploy to staging", "status": "done"},
                    ]
                },
            },
        }
    )

    # Sync everything
    print("\n3. Syncing control center...")
    result = await control_center_agent.handle_request({"type": "sync"})
    print(f"Sync result: {result}")


async def main():
    """Run the control center demo."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Initialize services
    remarkable_adapter = RemarkableAdapter()  # Would need proper initialization
    handwriting_adapter = HandwritingAdapter()  # Would need proper initialization

    remarkable_service = RemarkableService(remarkable_adapter)
    handwriting_service = HandwritingRecognitionService(handwriting_adapter)

    # Setup storage
    storage_path = Path.home() / ".inklink" / "control_center"
    storage_path.mkdir(parents=True, exist_ok=True)

    # Create control center agent
    config = AgentConfig(
        name="control_center",
        description="Manages the ink-based control interface",
        version="1.0.0",
        capabilities=["process_ink", "update_display", "sync_status"],
        mcp_enabled=True,
    )

    control_center_agent = ControlCenterAgent(
        config, remarkable_service, handwriting_service, storage_path
    )

    print("=== InkLink Control Center Demo ===")

    # Start the agent
    await control_center_agent.start()

    try:
        # Run visualization demo
        await demo_control_center_visualization(control_center_agent)

        # Simulate ink interactions
        await simulate_ink_interaction(control_center_agent)

        # Let it run for a bit
        print("\n\nControl center is running. Press Ctrl+C to stop...")
        await asyncio.sleep(30)

    except KeyboardInterrupt:
        print("\nStopping control center...")
    finally:
        await control_center_agent.stop()

    print("\nControl center demo completed.")


if __name__ == "__main__":
    asyncio.run(main())
