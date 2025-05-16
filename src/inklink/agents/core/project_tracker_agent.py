"""ProactiveProjectTrackerAgent for monitoring project progress and commitments."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from inklink.adapters.ollama_adapter import OllamaAdapter
from inklink.agents.base.agent import AgentConfig
from inklink.agents.base.mcp_integration import MCPCapability, MCPEnabledAgent


class ProactiveProjectTrackerAgent(MCPEnabledAgent):
    """Agent for tracking projects and commitments from speech and notes."""

    def __init__(
        self,
        config: AgentConfig,
        ollama_adapter: OllamaAdapter,
        storage_path: Path,
        check_interval: int = 3600,
    ):  # Check every hour
        """Initialize the project tracker agent."""
        super().__init__(config)
        self.ollama_adapter = ollama_adapter
        self.storage_path = storage_path
        self.check_interval = check_interval
        self._projects: Dict[str, Dict[str, Any]] = {}
        self._commitments: List[Dict[str, Any]] = []
        self._setup_mcp_capabilities()
        self._load_existing_data()

    def _setup_mcp_capabilities(self) -> None:
        """Set up MCP capabilities for project tracking."""
        # Get project status
        self.register_mcp_capability(
            MCPCapability(
                name="get_project_status",
                description="Get status of a specific project",
                handler=self._handle_get_project_status,
                input_schema={
                    "type": "object",
                    "properties": {"project_name": {"type": "string"}},
                    "required": ["project_name"],
                },
            )
        )

        # List all projects
        self.register_mcp_capability(
            MCPCapability(
                name="list_projects",
                description="List all tracked projects",
                handler=self._handle_list_projects,
            )
        )

        # Add commitment
        self.register_mcp_capability(
            MCPCapability(
                name="add_commitment",
                description="Add a new commitment or task",
                handler=self._handle_add_commitment,
                input_schema={
                    "type": "object",
                    "properties": {
                        "commitment": {"type": "string"},
                        "project": {"type": "string"},
                        "due_date": {"type": "string", "format": "date"},
                        "source": {"type": "string"},
                    },
                    "required": ["commitment"],
                },
            )
        )

        # Get commitments
        self.register_mcp_capability(
            MCPCapability(
                name="get_commitments",
                description="Get commitments for a project or time period",
                handler=self._handle_get_commitments,
                input_schema={
                    "type": "object",
                    "properties": {
                        "project": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "completed", "overdue"],
                        },
                        "time_period": {"type": "string"},
                    },
                },
            )
        )

    def _load_existing_data(self) -> None:
        """Load existing project and commitment data."""
        try:
            # Load projects
            projects_file = self.storage_path / "projects" / "projects.json"
            if projects_file.exists():
                with open(projects_file, "r") as f:
                    self._projects = json.load(f)

            # Load commitments
            commitments_file = self.storage_path / "projects" / "commitments.json"
            if commitments_file.exists():
                with open(commitments_file, "r") as f:
                    self._commitments = json.load(f)

        except Exception as e:
            self.logger.error(f"Error loading existing data: {e}")

    def _save_data(self) -> None:
        """Save project and commitment data."""
        try:
            # Create directory if needed
            projects_dir = self.storage_path / "projects"
            projects_dir.mkdir(parents=True, exist_ok=True)

            # Save projects
            with open(projects_dir / "projects.json", "w") as f:
                json.dump(self._projects, f, indent=2)

            # Save commitments
            with open(projects_dir / "commitments.json", "w") as f:
                json.dump(self._commitments, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving data: {e}")

    async def _agent_logic(self) -> None:
        """Main agent logic - monitor for updates and check status."""
        while not self._stop_event.is_set():
            try:
                # Check for spoken commitments
                await self._check_spoken_commitments()

                # Update project statuses
                await self._update_project_statuses()

                # Check for overdue commitments
                await self._check_overdue_commitments()

                # Save updated data
                self._save_data()

                # Wait for next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                self.logger.error(f"Error in agent logic: {e}")
                await asyncio.sleep(60)

    async def _check_spoken_commitments(self) -> None:
        """Check for new commitments in spoken data."""
        try:
            # Get recent spoken context about commitments
            response = await self.send_mcp_message(
                target="agent_limitless_insight",
                capability="find_spoken_context",
                data={
                    "topic": "commit OR promise OR will do OR deadline",
                    "time_period": "last_24_hours",
                },
            )

            contexts = response.get("contexts", [])

            for context in contexts:
                # Analyze context for commitments
                analysis_prompt = """
                Analyze this spoken text for any commitments, deadlines, or promises made.
                Extract:
                1. What was committed to
                2. Any deadline mentioned
                3. Related project (if mentioned)
                4. Priority level

                Format as JSON.
                """

                analysis = await self.ollama_adapter.query(
                    self.config.ollama_model or "llama3:8b",
                    analysis_prompt,
                    context=context["context"],
                )

                # Parse and add commitments
                try:
                    commitment_data = json.loads(analysis)
                    if commitment_data.get("commitment"):
                        await self._add_commitment(
                            {
                                "commitment": commitment_data["commitment"],
                                "source": "spoken",
                                "timestamp": context["timestamp"],
                                "project": commitment_data.get("project"),
                                "deadline": commitment_data.get("deadline"),
                                "priority": commitment_data.get("priority", "medium"),
                            }
                        )
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse commitment analysis")

        except Exception as e:
            self.logger.error(f"Error checking spoken commitments: {e}")

    async def _update_project_statuses(self) -> None:
        """Update status of all projects based on recent activity."""
        for project_name, project_data in self._projects.items():
            try:
                # Get recent mentions of the project
                response = await self.send_mcp_message(
                    target="agent_limitless_insight",
                    capability="find_spoken_context",
                    data={"topic": project_name, "time_period": "last_7_days"},
                )

                insights = response.get("insights", "")

                # Analyze project status
                status_prompt = f"""
                Based on this information about project '{project_name}', determine:
                1. Current status (active, on_hold, completed, at_risk)
                2. Recent progress made
                3. Any blockers or concerns
                4. Next steps

                Previous status: {project_data.get('status', 'unknown')}

                Format as JSON.
                """

                status_analysis = await self.ollama_adapter.query(
                    self.config.ollama_model or "llama3:8b",
                    status_prompt,
                    context=insights,
                )

                # Update project data
                try:
                    analysis_data = json.loads(status_analysis)
                    project_data.update(
                        {
                            "status": analysis_data.get(
                                "status", project_data.get("status")
                            ),
                            "last_update": datetime.now().isoformat(),
                            "recent_progress": analysis_data.get("progress"),
                            "blockers": analysis_data.get("blockers"),
                            "next_steps": analysis_data.get("next_steps"),
                        }
                    )
                except json.JSONDecodeError:
                    self.logger.warning(
                        f"Failed to parse status for project {project_name}"
                    )

            except Exception as e:
                self.logger.error(f"Error updating project {project_name}: {e}")

    async def _check_overdue_commitments(self) -> None:
        """Check for overdue commitments and send alerts."""
        now = datetime.now()
        overdue_commitments = []

        for commitment in self._commitments:
            if commitment.get("status") == "pending":
                deadline_str = commitment.get("deadline")
                if deadline_str:
                    try:
                        deadline = datetime.fromisoformat(deadline_str)
                        if deadline < now:
                            commitment["status"] = "overdue"
                            overdue_commitments.append(commitment)
                    except ValueError:
                        pass

        if overdue_commitments:
            # Generate alert summary
            alert_prompt = f"""
            Create an alert summary for these overdue commitments:
            {json.dumps(overdue_commitments, indent=2)}

            Include recommendations for addressing each one.
            """

            alert_summary = await self.ollama_adapter.query(
                self.config.ollama_model or "llama3:8b", alert_prompt
            )

            # Send alert (could integrate with notification system)
            self.logger.warning(f"Overdue commitments alert: {alert_summary}")

    async def _add_commitment(self, commitment_data: Dict[str, Any]) -> None:
        """Add a new commitment."""
        commitment = {
            "id": f"commit_{datetime.now().timestamp()}",
            "commitment": commitment_data["commitment"],
            "source": commitment_data.get("source", "manual"),
            "timestamp": commitment_data.get("timestamp", datetime.now().isoformat()),
            "project": commitment_data.get("project"),
            "deadline": commitment_data.get("deadline"),
            "priority": commitment_data.get("priority", "medium"),
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }

        self._commitments.append(commitment)

        # Link to project if specified
        project = commitment_data.get("project")
        if project:
            if project not in self._projects:
                self._projects[project] = {
                    "name": project,
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                }

            if "commitments" not in self._projects[project]:
                self._projects[project]["commitments"] = []

            self._projects[project]["commitments"].append(commitment["id"])

    async def _handle_get_project_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project status request."""
        project_name = data.get("project_name")

        if project_name in self._projects:
            return self._projects[project_name]
        else:
            return {"error": f"Project '{project_name}' not found"}

    async def _handle_list_projects(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list projects request."""
        return {"projects": list(self._projects.values()), "count": len(self._projects)}

    async def _handle_add_commitment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle add commitment request."""
        await self._add_commitment(data)
        return {"status": "added", "commitment": data.get("commitment")}

    async def _handle_get_commitments(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get commitments request."""
        project = data.get("project")
        status = data.get("status")
        time_period = data.get("time_period")

        filtered_commitments = self._commitments

        # Filter by project
        if project:
            project_data = self._projects.get(project, {})
            commitment_ids = set(project_data.get("commitments", []))
            filtered_commitments = [
                c for c in filtered_commitments if c["id"] in commitment_ids
            ]

        # Filter by status
        if status:
            filtered_commitments = [
                c for c in filtered_commitments if c.get("status") == status
            ]

        # Filter by time period
        if time_period:
            # Simple implementation for "last_7_days"
            if time_period == "last_7_days":
                cutoff = datetime.now() - timedelta(days=7)
                filtered_commitments = [
                    c
                    for c in filtered_commitments
                    if datetime.fromisoformat(c["created_at"]) > cutoff
                ]

        return {"commitments": filtered_commitments, "count": len(filtered_commitments)}

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests to the agent."""
        request_type = request.get("type")

        if request_type == "create_project":
            project_name = request.get("name")
            if project_name:
                self._projects[project_name] = {
                    "name": project_name,
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                    "description": request.get("description", ""),
                }
                self._save_data()
                return {"status": "created", "project": project_name}

        elif request_type == "update_commitment":
            commitment_id = request.get("commitment_id")
            updates = request.get("updates", {})

            for commitment in self._commitments:
                if commitment["id"] == commitment_id:
                    commitment.update(updates)
                    self._save_data()
                    return {"status": "updated", "commitment": commitment}

            return {"error": f"Commitment {commitment_id} not found"}

        else:
            return {"error": f"Unknown request type: {request_type}"}
