"""ControlCenterAgent for managing the ink-based control interface."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from inklink.agents.base.agent import AgentConfig
from inklink.agents.base.mcp_integration import MCPCapability, MCPEnabledAgent
from inklink.control_center import InkControlCenter
from inklink.control_center.core import AgentManager
from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)
from inklink.services.remarkable_service import RemarkableService


class ControlCenterAgent(MCPEnabledAgent):
    """Agent that manages the ink-based control center."""

    def __init__(
        self,
        config: AgentConfig,
        remarkable_service: RemarkableService,
        handwriting_service: HandwritingRecognitionService,
        storage_path: Path,
    ):
        """Initialize the control center agent."""
        super().__init__(config)
        self.remarkable_service = remarkable_service
        self.handwriting_service = handwriting_service
        self.storage_path = storage_path

        # Initialize control center
        self.agent_manager = AgentManager()
        self.control_center = InkControlCenter(
            remarkable_service, handwriting_service, self.agent_manager
        )

        # Setup MCP capabilities
        self._setup_mcp_capabilities()

        # State tracking
        self.notebook_id = None
        self.last_sync = datetime.now()

    def _setup_mcp_capabilities(self) -> None:
        """Set up MCP capabilities for the control center."""
        # Process ink input
        self.register_mcp_capability(
            MCPCapability(
                name="process_ink_input",
                description="Process handwritten input from the control center",
                handler=self._handle_process_ink_input,
                input_schema={
                    "type": "object",
                    "properties": {
                        "strokes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "points": {"type": "array"},
                                    "pressure": {"type": "array"},
                                    "timestamp": {"type": "number"},
                                },
                            },
                        },
                        "page_id": {"type": "string"},
                        "zone_id": {"type": "string"},
                    },
                    "required": ["strokes"],
                },
            )
        )

        # Update display
        self.register_mcp_capability(
            MCPCapability(
                name="update_display",
                description="Update the control center display",
                handler=self._handle_update_display,
                input_schema={
                    "type": "object",
                    "properties": {
                        "zone_id": {"type": "string"},
                        "update_type": {"type": "string"},
                        "data": {"type": "object"},
                    },
                },
            )
        )

        # Generate notebook
        self.register_mcp_capability(
            MCPCapability(
                name="generate_notebook",
                description="Generate or update the control center notebook",
                handler=self._handle_generate_notebook,
            )
        )

        # Sync status
        self.register_mcp_capability(
            MCPCapability(
                name="sync_status",
                description="Sync control center status with all agents",
                handler=self._handle_sync_status,
            )
        )

        # Execute command
        self.register_mcp_capability(
            MCPCapability(
                name="execute_command",
                description="Execute a control center command",
                handler=self._handle_execute_command,
                input_schema={
                    "type": "object",
                    "properties": {
                        "command_type": {"type": "string"},
                        "parameters": {"type": "object"},
                    },
                    "required": ["command_type"],
                },
            )
        )

    async def _agent_logic(self) -> None:
        """Main agent logic - monitor and sync control center."""
        while not self._stop_event.is_set():
            try:
                # Auto-sync every 5 minutes
                if (datetime.now() - self.last_sync).seconds > 300:
                    await self._sync_control_center()
                    self.last_sync = datetime.now()

                # Check for notebook updates
                if self.notebook_id:
                    await self._check_notebook_updates()

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                self.logger.error(f"Error in control center logic: {e}")
                await asyncio.sleep(30)

    async def _handle_process_ink_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process ink input from the control center."""
        strokes_data = data.get("strokes", [])

        # Convert stroke data to Stroke objects
        from inklink.control_center.processor import Stroke

        strokes = []
        for stroke_data in strokes_data:
            stroke = Stroke(
                points=stroke_data["points"],
                pressure=stroke_data.get("pressure", []),
                timestamp=stroke_data.get("timestamp", datetime.now().timestamp()),
            )
            strokes.append(stroke)

        # Process the strokes
        result = await self.control_center.process_ink_input(strokes)

        # Update the notebook if needed
        if result.get("commands"):
            await self._update_notebook()

        return result

    async def _handle_update_display(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update the control center display."""
        zone_id = data.get("zone_id")
        update_type = data.get("update_type")
        update_data = data.get("data", {})

        # Update specific zone
        if zone_id:
            zone = self.control_center.canvas.get_zone(zone_id)
            if zone:
                if update_type == "refresh":
                    await zone.refresh()
                elif update_type == "update":
                    await zone.update()
                elif update_type == "set_data":
                    # Zone-specific data update
                    if hasattr(zone, "set_data"):
                        await zone.set_data(update_data)
        else:
            # Update all zones
            await self.control_center.refresh_display()

        # Update the notebook
        await self._update_notebook()

        return {"status": "updated"}

    async def _handle_generate_notebook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate or update the control center notebook."""
        try:
            # Generate notebook data
            notebook_data = await self.control_center.generate_notebook()

            # Create or update notebook on reMarkable
            if self.notebook_id:
                # Update existing notebook
                await self.remarkable_service.update_notebook(
                    self.notebook_id, notebook_data
                )
            else:
                # Create new notebook
                self.notebook_id = await self.remarkable_service.create_notebook(
                    title="InkLink Control Center", content=notebook_data
                )

            # Save notebook ID
            await self._save_state()

            return {"status": "success", "notebook_id": self.notebook_id}

        except Exception as e:
            self.logger.error(f"Error generating notebook: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_sync_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sync control center status with all agents."""
        await self._sync_control_center()
        return {"status": "synced", "timestamp": datetime.now().isoformat()}

    async def _handle_execute_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a control center command."""
        command_type = data.get("command_type")
        parameters = data.get("parameters", {})

        # Create command object
        from inklink.control_center.processor import CommandType, InkCommand

        try:
            command = InkCommand(type=CommandType(command_type), parameters=parameters)

            # Execute command
            result = await self.control_center.execute_command(command)

            # Update notebook
            await self._update_notebook()

            return result

        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            return {"error": str(e)}

    async def _sync_control_center(self):
        """Sync control center with all agents and systems."""
        try:
            # Sync with all agents
            await self.control_center.sync_all()

            # Update notebook
            await self._update_notebook()

            self.last_sync = datetime.now()

        except Exception as e:
            self.logger.error(f"Error syncing control center: {e}")

    async def _check_notebook_updates(self):
        """Check for updates to the notebook on reMarkable."""
        try:
            # Get notebook modifications
            modifications = await self.remarkable_service.get_notebook_modifications(
                self.notebook_id, since=self.last_sync
            )

            if modifications:
                # Process any new ink strokes
                for mod in modifications:
                    if mod["type"] == "ink_added":
                        await self._handle_process_ink_input(
                            {
                                "strokes": mod["strokes"],
                                "page_id": mod["page_id"],
                                "zone_id": mod.get("zone_id"),
                            }
                        )

        except Exception as e:
            self.logger.error(f"Error checking notebook updates: {e}")

    async def _update_notebook(self):
        """Update the notebook with current state."""
        if self.notebook_id:
            try:
                # Generate updated notebook data
                notebook_data = await self.control_center.generate_notebook()

                # Update on reMarkable
                await self.remarkable_service.update_notebook(
                    self.notebook_id, notebook_data
                )

            except Exception as e:
                self.logger.error(f"Error updating notebook: {e}")

    async def _save_state(self):
        """Save control center state."""
        state_file = self.storage_path / "control_center_state.json"
        state_data = {
            "notebook_id": self.notebook_id,
            "last_sync": self.last_sync.isoformat(),
            "created_at": datetime.now().isoformat(),
        }

        with open(state_file, "w") as f:
            json.dump(state_data, f, indent=2)

    async def _load_state(self):
        """Load control center state."""
        state_file = self.storage_path / "control_center_state.json"
        if state_file.exists():
            with open(state_file, "r") as f:
                state_data = json.load(f)

            self.notebook_id = state_data.get("notebook_id")
            last_sync_str = state_data.get("last_sync")
            if last_sync_str:
                self.last_sync = datetime.fromisoformat(last_sync_str)

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests to the agent."""
        request_type = request.get("type")

        if request_type == "create_control_center":
            return await self._handle_generate_notebook({})

        if request_type == "process_ink":
            return await self._handle_process_ink_input(request.get("data", {}))

        if request_type == "sync":
            return await self._handle_sync_status({})
        return {"error": f"Unknown request type: {request_type}"}

    async def start(self):
        """Start the control center agent."""
        # Load saved state
        await self._load_state()

        # Create notebook if it doesn't exist
        if not self.notebook_id:
            await self._handle_generate_notebook({})

        # Start main agent logic
        await super().start()

    async def stop(self):
        """Stop the control center agent."""
        # Save state before stopping
        await self._save_state()

        await super().stop()
