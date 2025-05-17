"""Enhanced core control center implementation with improved state management."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)
from inklink.services.remarkable_service import RemarkableService

from .canvas import DynamicCanvas
from .processor import CommandType, InkCommand, InkProcessor
from .state_manager import ControlCenterState, StateEvent, StateEventType


class EnhancedInkControlCenter:
    """Enhanced control center coordinator with robust state management."""

    def __init__(
        self,
        remarkable_service: RemarkableService,
        handwriting_service: HandwritingRecognitionService,
        agent_manager: "AgentManager",
        state_file: Optional[Path] = None,
    ):
        """Initialize the enhanced control center."""
        self.canvas = DynamicCanvas()
        self.ink_processor = InkProcessor(handwriting_service)
        self.remarkable_service = remarkable_service
        self.agent_manager = agent_manager
        self.sync_service = EnhancedSyncService()

        # Initialize state manager
        self.state = ControlCenterState(persistence_path=state_file)

        # Initialize zones
        self._setup_zones()

        # Set up event handlers
        self._setup_event_handlers()

        # Recovery from persisted state
        asyncio.create_task(self._recover_state())

    def _setup_zones(self):
        """Initialize the default zones with state management."""
        from .zones import (
            AgentDashboardZone,
            DiscussionZone,
            KanbanZone,
            QuickActionsZone,
            RoadmapZone,
        )

        # Zone configuration
        zone_configs = [
            ("roadmap", RoadmapZone(), (0, 0), (400, 300)),
            ("kanban", KanbanZone(), (400, 0), (400, 300)),
            ("agents", AgentDashboardZone(), (800, 0), (400, 300)),
            ("discussion", DiscussionZone(), (0, 300), (1200, 200)),
            ("actions", QuickActionsZone(), (0, 500), (1200, 100)),
        ]

        # Create zones and update state
        for zone_id, zone, position, size in zone_configs:
            self.canvas.add_zone(zone_id, zone, position=position, size=size)

            # Initialize zone state
            asyncio.create_task(
                self.state.update_zone(
                    zone_id,
                    {
                        "title": zone.title,
                        "position": position,
                        "size": size,
                        "elements": {},
                        "active": True,
                    },
                )
            )

    def _setup_event_handlers(self):
        """Set up state event handlers."""
        # Handle zone updates
        self.state.add_event_listener(
            StateEventType.ZONE_UPDATED, self._handle_zone_update
        )

        # Handle selection changes
        self.state.add_event_listener(
            StateEventType.SELECTION_CHANGED, self._handle_selection_change
        )

        # Handle errors
        self.state.add_event_listener(StateEventType.ERROR_OCCURRED, self._handle_error)

    async def _recover_state(self):
        """Recover from persisted state on startup."""
        try:
            # Get the last snapshot
            snapshot = await self.state.get_snapshot()

            # Restore zone configurations
            for zone_id, zone_data in snapshot.zones.items():
                if zone_id in self.canvas.zones:
                    zone = self.canvas.get_zone(zone_id)
                    # Restore zone-specific state
                    if hasattr(zone, "restore_state"):
                        await zone.restore_state(zone_data)

            # Restore selections
            if snapshot.selections:
                await self.state.update_selection(snapshot.selections)

            logger.info("Successfully recovered control center state")

        except Exception as e:
            logger.error(f"Failed to recover state: {e}")

    async def process_ink_input(self, strokes: List["Stroke"]) -> Dict[str, Any]:
        """Process handwritten input with state tracking."""
        try:
            # Detect gestures
            gestures = await self.ink_processor.detect_gestures(strokes)

            # Track gesture state
            for gesture in gestures:
                await self.state.add_gesture(
                    {
                        "type": gesture.type,
                        "confidence": gesture.confidence,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # Find which zone was interacted with
            zone_id = self.canvas.find_zone_at_position(strokes[0].start_point)

            if zone_id:
                zone = self.canvas.get_zone(zone_id)

                # Update zone state
                zone_state = await self.state.get_zone(zone_id)
                zone_state["last_interaction"] = datetime.now().isoformat()
                await self.state.update_zone(zone_id, zone_state)

                # Let the zone handle the strokes
                zone_result = await zone.handle_strokes(strokes)

                if zone_result.get("handled"):
                    return zone_result

            # Extract text
            text = await self.ink_processor.recognize_text(strokes)

            # Parse commands
            commands = self.ink_processor.parse_commands(text, gestures)

            # Execute commands with state tracking
            results = []
            for command in commands:
                result = await self.execute_command(command)
                results.append(result)

                # Track command execution
                await self.state._emit_event(
                    StateEvent(
                        event_type=StateEventType.COMMAND_EXECUTED,
                        timestamp=datetime.now(),
                        data={"command": command.type.value, "result": result},
                    )
                )

            # Update canvas
            await self.canvas.update()

            # Clear gestures after processing
            await self.state.clear_gestures()

            return {
                "commands": len(commands),
                "results": results,
                "gestures": [g.type for g in gestures],
                "text": text,
            }

        except Exception as e:
            logger.error(f"Error processing ink input: {e}")
            await self.state._emit_event(
                StateEvent(
                    event_type=StateEventType.ERROR_OCCURRED,
                    timestamp=datetime.now(),
                    error=str(e),
                    data={"context": "process_ink_input"},
                )
            )
            raise

    async def execute_command(self, command: InkCommand) -> Dict[str, Any]:
        """Execute a parsed command with state tracking."""
        if command.type == CommandType.AGENT_INSTRUCTION:
            return await self._execute_agent_instruction(command)
        if command.type == CommandType.CREATE_TASK:
            return await self._execute_create_task(command)
        if command.type == CommandType.ASSIGN_TASK:
            return await self._execute_assign_task(command)
        if command.type == CommandType.COMPLETE_TASK:
            return await self._execute_complete_task(command)
        if command.type == CommandType.QUICK_ACTION:
            return await self._execute_quick_action(command)
        return {"error": f"Unknown command type: {command.type}"}

    async def _execute_agent_instruction(self, command: InkCommand) -> Dict[str, Any]:
        """Execute an agent instruction command with state updates."""
        agent_name = command.target
        instruction = command.parameters.get("instruction")

        # Update agent state to indicate pending instruction
        agents_zone_state = await self.state.get_zone("agents")
        if "elements" not in agents_zone_state:
            agents_zone_state["elements"] = {}

        agents_zone_state["elements"][agent_name] = {
            "status": "executing",
            "last_instruction": instruction,
            "timestamp": datetime.now().isoformat(),
        }
        await self.state.update_zone("agents", agents_zone_state)

        # Send instruction to agent
        response = await self.agent_manager.send_to_agent(
            agent_name, "execute_instruction", {"instruction": instruction}
        )

        # Update agent dashboard with response
        agents_zone = self.canvas.get_zone("agents")
        await agents_zone.update_agent_status(agent_name, response)

        # Update state with result
        agents_zone_state["elements"][agent_name].update(
            {
                "status": "completed",
                "response": response,
                "completed_at": datetime.now().isoformat(),
            }
        )
        await self.state.update_zone("agents", agents_zone_state)

        return {"agent": agent_name, "instruction": instruction, "response": response}

    async def _execute_create_task(self, command: InkCommand) -> Dict[str, Any]:
        """Create a new task with state tracking."""
        task_data = command.parameters

        # Generate task ID
        task_id = f"task_{datetime.now().timestamp()}"

        # Add to kanban state
        await self.state.add_element(
            "kanban",
            task_id,
            {
                **task_data,
                "created_at": datetime.now().isoformat(),
                "status": "new",
                "column": "todo",
            },
        )

        # Create task in kanban
        kanban_zone = self.canvas.get_zone("kanban")
        await kanban_zone.create_task(task_data)

        # Sync with task system
        await self.sync_service.create_task(task_data)

        return {"task_id": task_id, "task": task_data}

    async def _execute_assign_task(self, command: InkCommand) -> Dict[str, Any]:
        """Assign a task to an agent with state updates."""
        task_id = command.parameters.get("task_id")
        agent_name = command.parameters.get("agent_name")

        # Update task state
        await self.state.update_element(
            "kanban",
            task_id,
            {
                "assigned_to": agent_name,
                "assigned_at": datetime.now().isoformat(),
                "status": "assigned",
            },
        )

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
        """Mark a task as complete with state tracking."""
        task_id = command.parameters.get("task_id")

        # Update task state
        await self.state.update_element(
            "kanban",
            task_id,
            {
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "column": "done",
            },
        )

        # Update kanban
        kanban_zone = self.canvas.get_zone("kanban")
        await kanban_zone.complete_task(task_id)

        # Sync with task system
        await self.sync_service.complete_task(task_id)

        return {"task_id": task_id, "completed": True}

    async def _execute_quick_action(self, command: InkCommand) -> Dict[str, Any]:
        """Execute a quick action with state tracking."""
        action = command.parameters.get("action")

        if action == "sync":
            # Track sync state
            await self.state._emit_event(
                StateEvent(
                    event_type=StateEventType.SYNC_STARTED, timestamp=datetime.now()
                )
            )

            await self.sync_all()

            await self.state._emit_event(
                StateEvent(
                    event_type=StateEventType.SYNC_COMPLETED, timestamp=datetime.now()
                )
            )

            return {"action": "sync", "status": "completed"}

        if action == "refresh":
            await self.refresh_display()
            return {"action": "refresh", "status": "completed"}

        if action == "new_task":
            # Switch to task creation mode
            return {"action": "new_task", "mode": "create"}

        return {"error": f"Unknown action: {action}"}

    async def sync_all(self):
        """Sync all data with backend systems and update state."""
        try:
            # Sync tasks
            tasks = await self.sync_service.get_all_tasks()
            kanban_zone = self.canvas.get_zone("kanban")
            await kanban_zone.update_tasks(tasks)

            # Update task state
            kanban_state = await self.state.get_zone("kanban")
            kanban_state["last_sync"] = datetime.now().isoformat()
            await self.state.update_zone("kanban", kanban_state)

            # Sync agent status
            agent_status = await self.agent_manager.get_all_status()
            agents_zone = self.canvas.get_zone("agents")
            await agents_zone.update_all_agents(agent_status)

            # Update agent state
            agents_state = await self.state.get_zone("agents")
            agents_state["last_sync"] = datetime.now().isoformat()
            await self.state.update_zone("agents", agents_state)

            # Sync roadmap
            roadmap_data = await self.sync_service.get_roadmap()
            roadmap_zone = self.canvas.get_zone("roadmap")
            await roadmap_zone.update_roadmap(roadmap_data)

            # Update roadmap state
            roadmap_state = await self.state.get_zone("roadmap")
            roadmap_state["last_sync"] = datetime.now().isoformat()
            await self.state.update_zone("roadmap", roadmap_state)

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise

    async def refresh_display(self):
        """Refresh the entire display with state preservation."""
        # Save current state
        snapshot = await self.state.get_snapshot()

        # Refresh canvas
        await self.canvas.refresh()

        # Sync with backend
        await self.sync_all()

        # Restore selections and gestures
        await self.state.update_selection(snapshot.selections)
        self.state._active_gestures = snapshot.active_gestures

    async def generate_notebook(self) -> bytes:
        """Generate the control center as a reMarkable notebook with state."""
        # Create notebook structure
        notebook_data = {
            "title": "InkLink Control Center",
            "created": datetime.now().isoformat(),
            "pages": [],
            "state_version": self.state._version,
        }

        # Generate pages from zones with state
        for zone_id, zone in self.canvas.zones.items():
            zone_state = await self.state.get_zone(zone_id)
            page_data = await zone.generate_page()

            # Include state metadata in page
            page_data["state"] = zone_state

            notebook_data["pages"].append(
                {"id": zone_id, "title": zone.title, "content": page_data}
            )

        # Convert to reMarkable format
        return await self.remarkable_service.create_notebook(notebook_data)

    # Event handlers
    @staticmethod
    async def _handle_zone_update(event: StateEvent):
        """Handle zone update events."""
        logger.info(f"Zone {event.zone_id} updated")

    @staticmethod
    async def _handle_selection_change(event: StateEvent):
        """Handle selection change events."""
        logger.info(f"Selection changed: {event.data}")

    @staticmethod
    async def _handle_error(event: StateEvent):
        """Handle error events."""
        logger.error(f"Error occurred: {event.error}")


class EnhancedSyncService:
    """Enhanced sync service with state tracking and recovery."""

    def __init__(self):
        self.websocket = None
        self.update_queue = asyncio.Queue()
        self.connected = False
        self.retry_count = 0
        self.max_retries = 3

    async def connect(self, url: str):
        """Connect to the backend sync service with retry logic."""
        from inklink.utils.retry import retry

        @retry(max_attempts=self.max_retries, base_delay=2.0)
        async def _connect():
            # Implementation would connect to WebSocket
            self.connected = True
            logger.info("Connected to sync service")

        await _connect()

    async def create_task(self, task_data: Dict[str, Any]):
        """Create a task in the backend with state tracking."""
        if not self.connected:
            await self.update_queue.put(("create_task", task_data))
            return

        # Implementation would send to backend
        logger.info(f"Created task: {task_data}")

    async def complete_task(self, task_id: str):
        """Complete a task in the backend."""
        if not self.connected:
            await self.update_queue.put(("complete_task", task_id))
            return

        # Implementation would send to backend
        logger.info(f"Completed task: {task_id}")

    @staticmethod
    async def get_all_tasks() -> List[Dict[str, Any]]:
        """Get all tasks from the backend."""
        # Implementation would fetch from backend
        return []

    @staticmethod
    async def get_roadmap() -> Dict[str, Any]:
        """Get roadmap data from the backend."""
        # Implementation would fetch from backend
        return {}

    async def process_queue(self):
        """Process queued updates when connection is restored."""
        while not self.update_queue.empty():
            operation, data = await self.update_queue.get()

            if operation == "create_task":
                await self.create_task(data)
            elif operation == "complete_task":
                await self.complete_task(data)

            logger.info(f"Processed queued operation: {operation}")


# Import logger
logger = logging.getLogger(__name__)
