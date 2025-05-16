"""Core control center implementation."""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from inklink.agents.base.mcp_integration import MCPEnabledAgent, MCPCapability
from inklink.agents.base.agent import AgentConfig
from inklink.services.remarkable_service import RemarkableService
from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)

from .canvas import DynamicCanvas
from .processor import InkProcessor, InkCommand, CommandType
from .zones import BaseZone


class InkControlCenter:
    """Main control center coordinator for ink-based agent management."""

    def __init__(
        self,
        remarkable_service: RemarkableService,
        handwriting_service: HandwritingRecognitionService,
        agent_manager: "AgentManager",
    ):
        """Initialize the control center."""
        self.canvas = DynamicCanvas()
        self.ink_processor = InkProcessor(handwriting_service)
        self.remarkable_service = remarkable_service
        self.agent_manager = agent_manager
        self.sync_service = SyncService()

        # Initialize zones
        self._setup_zones()

        # State tracking
        self.selected_items: List[str] = []
        self.active_gestures: List["Gesture"] = []
        self.last_update = datetime.now()

    def _setup_zones(self):
        """Initialize the default zones."""
        from .zones import (
            RoadmapZone,
            KanbanZone,
            AgentDashboardZone,
            DiscussionZone,
            QuickActionsZone,
        )

        # Create zone layout
        self.canvas.add_zone("roadmap", RoadmapZone(), position=(0, 0), size=(400, 300))
        self.canvas.add_zone("kanban", KanbanZone(), position=(400, 0), size=(400, 300))
        self.canvas.add_zone(
            "agents", AgentDashboardZone(), position=(800, 0), size=(400, 300)
        )
        self.canvas.add_zone(
            "discussion", DiscussionZone(), position=(0, 300), size=(1200, 200)
        )
        self.canvas.add_zone(
            "actions", QuickActionsZone(), position=(0, 500), size=(1200, 100)
        )

    async def process_ink_input(self, strokes: List["Stroke"]) -> Dict[str, Any]:
        """Process handwritten input and execute commands."""
        # Detect gestures
        gestures = await self.ink_processor.detect_gestures(strokes)

        # Find which zone was interacted with
        zone_id = self.canvas.find_zone_at_position(strokes[0].start_point)

        if zone_id:
            zone = self.canvas.get_zone(zone_id)

            # Let the zone handle the strokes first
            zone_result = await zone.handle_strokes(strokes)

            if zone_result.get("handled"):
                return zone_result

        # Extract text
        text = await self.ink_processor.recognize_text(strokes)

        # Parse commands
        commands = self.ink_processor.parse_commands(text, gestures)

        # Execute commands
        results = []
        for command in commands:
            result = await self.execute_command(command)
            results.append(result)

        # Update canvas
        await self.canvas.update()

        return {
            "commands": len(commands),
            "results": results,
            "gestures": [g.type for g in gestures],
            "text": text,
        }

    async def execute_command(self, command: InkCommand) -> Dict[str, Any]:
        """Execute a parsed command."""
        if command.type == CommandType.AGENT_INSTRUCTION:
            return await self._execute_agent_instruction(command)
        elif command.type == CommandType.CREATE_TASK:
            return await self._execute_create_task(command)
        elif command.type == CommandType.ASSIGN_TASK:
            return await self._execute_assign_task(command)
        elif command.type == CommandType.COMPLETE_TASK:
            return await self._execute_complete_task(command)
        elif command.type == CommandType.QUICK_ACTION:
            return await self._execute_quick_action(command)
        else:
            return {"error": f"Unknown command type: {command.type}"}

    async def _execute_agent_instruction(self, command: InkCommand) -> Dict[str, Any]:
        """Execute an agent instruction command."""
        agent_name = command.target
        instruction = command.parameters.get("instruction")

        # Send instruction to agent
        response = await self.agent_manager.send_to_agent(
            agent_name, "execute_instruction", {"instruction": instruction}
        )

        # Update agent dashboard
        agents_zone = self.canvas.get_zone("agents")
        await agents_zone.update_agent_status(agent_name, response)

        return {"agent": agent_name, "instruction": instruction, "response": response}

    async def _execute_create_task(self, command: InkCommand) -> Dict[str, Any]:
        """Create a new task."""
        task_data = command.parameters

        # Create task in kanban
        kanban_zone = self.canvas.get_zone("kanban")
        task_id = await kanban_zone.create_task(task_data)

        # Sync with task system
        await self.sync_service.create_task(task_data)

        return {"task_id": task_id, "task": task_data}

    async def _execute_assign_task(self, command: InkCommand) -> Dict[str, Any]:
        """Assign a task to an agent."""
        task_id = command.parameters.get("task_id")
        agent_name = command.parameters.get("agent_name")

        # Update kanban
        kanban_zone = self.canvas.get_zone("kanban")
        await kanban_zone.assign_task(task_id, agent_name)

        # Send to agent
        response = await self.agent_manager.send_to_agent(
            agent_name, "accept_task", {"task_id": task_id}
        )

        return {
            "task_id": task_id,
            "agent": agent_name,
            "accepted": response.get("accepted", False),
        }

    async def _execute_complete_task(self, command: InkCommand) -> Dict[str, Any]:
        """Mark a task as complete."""
        task_id = command.parameters.get("task_id")

        # Update kanban
        kanban_zone = self.canvas.get_zone("kanban")
        await kanban_zone.complete_task(task_id)

        # Sync with task system
        await self.sync_service.complete_task(task_id)

        return {"task_id": task_id, "completed": True}

    async def _execute_quick_action(self, command: InkCommand) -> Dict[str, Any]:
        """Execute a quick action."""
        action = command.parameters.get("action")

        if action == "sync":
            await self.sync_all()
            return {"action": "sync", "status": "completed"}
        elif action == "refresh":
            await self.refresh_display()
            return {"action": "refresh", "status": "completed"}
        elif action == "new_task":
            # Switch to task creation mode
            return {"action": "new_task", "mode": "create"}
        else:
            return {"error": f"Unknown action: {action}"}

    async def sync_all(self):
        """Sync all data with backend systems."""
        # Sync tasks
        tasks = await self.sync_service.get_all_tasks()
        kanban_zone = self.canvas.get_zone("kanban")
        await kanban_zone.update_tasks(tasks)

        # Sync agent status
        agent_status = await self.agent_manager.get_all_status()
        agents_zone = self.canvas.get_zone("agents")
        await agents_zone.update_all_agents(agent_status)

        # Sync roadmap
        roadmap_data = await self.sync_service.get_roadmap()
        roadmap_zone = self.canvas.get_zone("roadmap")
        await roadmap_zone.update_roadmap(roadmap_data)

    async def refresh_display(self):
        """Refresh the entire display."""
        await self.canvas.refresh()
        await self.sync_all()

    async def generate_notebook(self) -> bytes:
        """Generate the control center as a reMarkable notebook."""
        # Create notebook structure
        notebook_data = {
            "title": "InkLink Control Center",
            "created": datetime.now().isoformat(),
            "pages": [],
        }

        # Generate pages from zones
        for zone_id, zone in self.canvas.zones.items():
            page_data = await zone.generate_page()
            notebook_data["pages"].append(
                {"id": zone_id, "title": zone.title, "content": page_data}
            )

        # Convert to reMarkable format
        return await self.remarkable_service.create_notebook(notebook_data)


class SyncService:
    """Handles synchronization between ink interface and backend systems."""

    def __init__(self):
        self.websocket = None
        self.update_queue = asyncio.Queue()
        self.connected = False

    async def connect(self, url: str):
        """Connect to the backend sync service."""
        # Implementation would connect to WebSocket
        self.connected = True

    async def create_task(self, task_data: Dict[str, Any]):
        """Create a task in the backend."""
        if not self.connected:
            return

        await self.update_queue.put({"type": "create_task", "data": task_data})

    async def complete_task(self, task_id: str):
        """Mark a task as complete in the backend."""
        if not self.connected:
            return

        await self.update_queue.put({"type": "complete_task", "task_id": task_id})

    async def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks from the backend."""
        # Mock implementation
        return [
            {"id": "1", "title": "Fix MCP bug", "status": "todo", "tags": ["urgent"]},
            {
                "id": "2",
                "title": "Ollama adapter",
                "status": "doing",
                "assigned": "Limitless",
            },
            {"id": "3", "title": "Base agent", "status": "done"},
        ]

    async def get_roadmap(self) -> Dict[str, Any]:
        """Get roadmap data from the backend."""
        # Mock implementation
        return {
            "milestones": [
                {
                    "id": "q1",
                    "title": "Q1 Goals",
                    "items": [
                        {"title": "Agent Framework", "status": "done"},
                        {"title": "MCP Support", "status": "done"},
                        {"title": "Ollama Integration", "status": "in_progress"},
                    ],
                }
            ]
        }


class AgentManager:
    """Manages communication with agents."""

    def __init__(self):
        self.agents = {}

    async def send_to_agent(
        self, agent_name: str, capability: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a message to a specific agent."""
        # Mock implementation
        return {
            "status": "received",
            "agent": agent_name,
            "response": f"Executing {capability}",
        }

    async def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all agents."""
        # Mock implementation
        return {
            "Limitless": {
                "status": "running",
                "last_action": "Processed 5 transcripts",
                "next_action": "Check in 5 min",
            },
            "Briefing": {
                "status": "processing",
                "current_task": "Generating daily summary",
                "eta": "2 min",
            },
            "Tracker": {"status": "idle", "stats": {"projects": 12, "alerts": 2}},
        }
