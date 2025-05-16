"""Zone implementations for the control center."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .processor import Stroke


@dataclass
class ZoneElement:
    """Base class for elements within a zone."""

    id: str
    position: Tuple[int, int]
    size: Tuple[int, int]
    content: Any
    interactive: bool = True
    selected: bool = False


class BaseZone(ABC):
    """Base class for all zones."""

    def __init__(self, title: str = ""):
        """Initialize the zone."""
        self.title = title
        self.elements: Dict[str, ZoneElement] = {}
        self.dirty = True

    @abstractmethod
    async def handle_strokes(self, strokes: List[Stroke]) -> Dict[str, Any]:
        """Handle ink strokes within this zone."""
        pass

    @abstractmethod
    async def update(self):
        """Update the zone's state."""
        pass

    @abstractmethod
    async def refresh(self):
        """Force a complete refresh of the zone."""
        pass

    @abstractmethod
    def render(self) -> Dict[str, Any]:
        """Render the zone's content."""
        pass

    @abstractmethod
    def to_svg(self, width: int, height: int) -> str:
        """Convert zone to SVG format."""
        pass

    @abstractmethod
    async def generate_page(self) -> Dict[str, Any]:
        """Generate page data for the notebook."""
        pass

    def add_element(self, element: ZoneElement):
        """Add an element to the zone."""
        self.elements[element.id] = element
        self.dirty = True

    def remove_element(self, element_id: str):
        """Remove an element from the zone."""
        if element_id in self.elements:
            del self.elements[element_id]
            self.dirty = True

    def find_element_at(self, position: Tuple[int, int]) -> Optional[ZoneElement]:
        """Find element at given position."""
        for element in self.elements.values():
            if element.interactive:
                x, y = element.position
                w, h = element.size
                if x <= position[0] <= x + w and y <= position[1] <= y + h:
                    return element
        return None


class RoadmapZone(BaseZone):
    """Zone for project roadmap visualization."""

    def __init__(self):
        """Initialize the roadmap zone."""
        super().__init__("Roadmap")
        self.milestones: List[Dict[str, Any]] = []
        self.timeline_start = datetime.now()
        self.timeline_end = datetime.now()

    async def handle_strokes(self, strokes: List[Stroke]) -> Dict[str, Any]:
        """Handle strokes for roadmap interaction."""
        # Check if drawing a milestone box
        if len(strokes) == 4:  # Potential box
            bounds = self._get_stroke_bounds(strokes)

            # Create new milestone
            milestone = {
                "id": f"milestone_{datetime.now().timestamp()}",
                "title": "New Milestone",
                "position": bounds[:2],
                "size": (bounds[2] - bounds[0], bounds[3] - bounds[1]),
                "items": [],
            }

            self.milestones.append(milestone)
            self.dirty = True

            return {
                "handled": True,
                "action": "created_milestone",
                "milestone": milestone,
            }

        return {"handled": False}

    async def update(self):
        """Update roadmap state."""
        # Update milestone statuses
        for milestone in self.milestones:
            completed = sum(
                1 for item in milestone["items"] if item["status"] == "done"
            )
            total = len(milestone["items"])
            milestone["progress"] = completed / total if total > 0 else 0

    async def refresh(self):
        """Refresh roadmap data."""
        # Would fetch latest roadmap data from backend
        pass

    def render(self) -> Dict[str, Any]:
        """Render the roadmap."""
        return {
            "type": "roadmap",
            "milestones": self.milestones,
            "timeline": {
                "start": self.timeline_start.isoformat(),
                "end": self.timeline_end.isoformat(),
            },
        }

    def to_svg(self, width: int, height: int) -> str:
        """Convert roadmap to SVG."""
        svg_parts = []

        # Draw timeline
        svg_parts.append(
            f'<line x1="50" y1="{height // 2}" x2="{width - 50}" y2="{height // 2}" '
            'stroke="black" stroke-width="2"/>'
        )

        # Draw milestones
        for milestone in self.milestones:
            x, y = milestone["position"]
            w, h = milestone["size"]

            # Milestone box
            svg_parts.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                'fill="lightblue" stroke="black" stroke-width="1"/>'
            )

            # Title
            svg_parts.append(
                f'<text x="{x + 5}" y="{y + 20}" font-size="14">{milestone["title"]}</text>'
            )

        return "\n".join(svg_parts)

    async def generate_page(self) -> Dict[str, Any]:
        """Generate page for the roadmap."""
        return {"title": "Roadmap", "content": self.render()}

    def _get_stroke_bounds(
        self, strokes: List[Stroke]
    ) -> Tuple[float, float, float, float]:
        """Get combined bounds of strokes."""
        all_points = []
        for stroke in strokes:
            all_points.extend(stroke.points)

        if not all_points:
            return (0, 0, 0, 0)

        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        return (min(xs), min(ys), max(xs), max(ys))


class KanbanZone(BaseZone):
    """Zone for kanban task management."""

    def __init__(self):
        """Initialize the kanban zone."""
        super().__init__("Tasks")
        self.columns = {
            "todo": {"title": "TODO", "tasks": []},
            "doing": {"title": "DOING", "tasks": []},
            "done": {"title": "DONE", "tasks": []},
        }
        self.selected_task = None

    async def handle_strokes(self, strokes: List[Stroke]) -> Dict[str, Any]:
        """Handle strokes for task interaction."""
        # Find which column was interacted with
        position = strokes[0].start_point if strokes else (0, 0)
        column = self._find_column_at(position)

        if column:
            # Check if creating new task
            if len(strokes) > 5:  # Handwritten text
                task = {
                    "id": f"task_{datetime.now().timestamp()}",
                    "title": "New Task",  # Would be recognized from handwriting
                    "status": column,
                    "created": datetime.now().isoformat(),
                }

                self.columns[column]["tasks"].append(task)
                self.dirty = True

                return {"handled": True, "action": "created_task", "task": task}

        return {"handled": False}

    async def create_task(self, task_data: Dict[str, Any]) -> str:
        """Create a new task."""
        task = {
            "id": f"task_{datetime.now().timestamp()}",
            "title": task_data.get("title", "New Task"),
            "tags": task_data.get("tags", []),
            "priority": task_data.get("priority", "normal"),
            "status": "todo",
            "created": datetime.now().isoformat(),
        }

        self.columns["todo"]["tasks"].append(task)
        self.dirty = True
        return task["id"]

    async def assign_task(self, task_id: str, agent_name: str):
        """Assign a task to an agent."""
        task = self._find_task(task_id)
        if task:
            task["assigned"] = agent_name
            self.dirty = True

    async def complete_task(self, task_id: str):
        """Mark a task as complete."""
        task = self._find_task(task_id)
        if task:
            # Remove from current column
            for column in self.columns.values():
                column["tasks"] = [t for t in column["tasks"] if t["id"] != task_id]

            # Add to done column
            task["status"] = "done"
            task["completed"] = datetime.now().isoformat()
            self.columns["done"]["tasks"].append(task)
            self.dirty = True

    async def update_tasks(self, tasks: List[Dict[str, Any]]):
        """Update all tasks from external source."""
        # Clear existing tasks
        for column in self.columns.values():
            column["tasks"] = []

        # Add new tasks
        for task in tasks:
            status = task.get("status", "todo")
            if status in self.columns:
                self.columns[status]["tasks"].append(task)

        self.dirty = True

    async def update(self):
        """Update kanban state."""
        # Could update task priorities, check deadlines, etc.
        pass

    async def refresh(self):
        """Refresh kanban data."""
        # Would fetch latest task data from backend
        pass

    def render(self) -> Dict[str, Any]:
        """Render the kanban board."""
        return {"type": "kanban", "columns": self.columns}

    def to_svg(self, width: int, height: int) -> str:
        """Convert kanban to SVG."""
        svg_parts = []

        # Calculate column width
        col_width = width // len(self.columns)

        # Draw columns
        for i, (col_id, column) in enumerate(self.columns.items()):
            x = i * col_width

            # Column header
            svg_parts.append(
                f'<rect x="{x}" y="0" width="{col_width - 5}" height="30" '
                'fill="lightgray" stroke="black" stroke-width="1"/>'
            )
            svg_parts.append(
                f'<text x="{x + 10}" y="20" font - size="16" font - weight="bold">'
                f'{column["title"]}</text>'
            )

            # Tasks
            y = 40
            for task in column["tasks"]:
                svg_parts.append(
                    f'<rect x="{x + 5}" y="{y}" width="{col_width - 15}" height="50" '
                    'fill="white" stroke="black" stroke-width="1"/>'
                )
                svg_parts.append(
                    f'<text x="{x + 10}" y="{y + 20}" font - size="12">{task["title"]}< / text>'
                )

                # Tags
                if task.get("tags"):
                    tags_text = " ".join(f"#{tag}" for tag in task["tags"])
                    svg_parts.append(
                        f'<text x="{x + 10}" y="{y + 35}" font - size="10" fill="blue">'
                        f"{tags_text}</text>"
                    )

                y += 60

        return "\n".join(svg_parts)

    async def generate_page(self) -> Dict[str, Any]:
        """Generate page for the kanban board."""
        return {"title": "Task Board", "content": self.render()}

    def _find_column_at(self, position: Tuple[int, int]) -> Optional[str]:
        """Find which column contains the position."""
        # Simple column detection based on x position
        x = position[0]
        col_width = 400  # Assuming 1200px width / 3 columns
        col_index = int(x // col_width)

        columns = list(self.columns.keys())
        if 0 <= col_index < len(columns):
            return columns[col_index]

        return None

    def _find_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Find a task by ID."""
        for column in self.columns.values():
            for task in column["tasks"]:
                if task["id"] == task_id:
                    return task
        return None


class AgentDashboardZone(BaseZone):
    """Zone for agent status and control."""

    def __init__(self):
        """Initialize the agent dashboard."""
        super().__init__("Agents")
        self.agents: Dict[str, Dict[str, Any]] = {}

    async def handle_strokes(self, strokes: List[Stroke]) -> Dict[str, Any]:
        """Handle strokes for agent interaction."""
        # Find which agent was selected
        position = strokes[0].start_point if strokes else (0, 0)
        agent = self._find_agent_at(position)

        if agent:
            # Toggle agent state with tap
            if len(strokes) == 1 and len(strokes[0].points) < 5:  # Tap
                await self._toggle_agent(agent)
                return {"handled": True, "action": "toggled_agent", "agent": agent}

        return {"handled": False}

    async def update_agent_status(self, agent_name: str, status: Dict[str, Any]):
        """Update status for a specific agent."""
        if agent_name not in self.agents:
            self.agents[agent_name] = {"name": agent_name}

        self.agents[agent_name].update(status)
        self.dirty = True

    async def update_all_agents(self, agent_statuses: Dict[str, Dict[str, Any]]):
        """Update all agent statuses."""
        self.agents = agent_statuses
        self.dirty = True

    async def update(self):
        """Update agent dashboard."""
        # Could check agent health, update metrics, etc.
        pass

    async def refresh(self):
        """Refresh agent data."""
        # Would fetch latest agent status from backend
        pass

    def render(self) -> Dict[str, Any]:
        """Render the agent dashboard."""
        return {"type": "agent_dashboard", "agents": self.agents}

    def to_svg(self, width: int, height: int) -> str:
        """Convert dashboard to SVG."""
        svg_parts = []

        y = 10
        for agent_name, agent_data in self.agents.items():
            # Agent box
            svg_parts.append(
                f'<rect x="10" y="{y}" width="{width - 20}" height="60" '
                'fill="lightgreen" stroke="black" stroke-width="1"/>'
            )

            # Agent name
            svg_parts.append(
                f'<text x="20" y="{y + 25}" font - size="16" font - weight="bold">'
                f"{agent_name}</text>"
            )

            # Status
            status = agent_data.get("status", "unknown")
            svg_parts.append(
                f'<text x="20" y="{y + 45}" font - size="12">'
                f"Status: {status}< / text>"
            )

            # Status indicator
            color = "green" if status == "running" else "orange"
            svg_parts.append(
                f'<circle cx="{width - 30}" cy="{y + 30}" r="10" fill="{color}" / >'
            )

            y += 70

        return "\n".join(svg_parts)

    async def generate_page(self) -> Dict[str, Any]:
        """Generate page for the dashboard."""
        return {"title": "Agent Dashboard", "content": self.render()}

    def _find_agent_at(self, position: Tuple[int, int]) -> Optional[str]:
        """Find which agent was clicked."""
        y = position[1]
        agent_height = 70
        agent_index = int(y // agent_height)

        agents = list(self.agents.keys())
        if 0 <= agent_index < len(agents):
            return agents[agent_index]

        return None

    async def _toggle_agent(self, agent_name: str):
        """Toggle agent running state."""
        if agent_name in self.agents:
            current_status = self.agents[agent_name].get("status", "stopped")
            new_status = "running" if current_status == "stopped" else "stopped"
            self.agents[agent_name]["status"] = new_status
            self.dirty = True


class DiscussionZone(BaseZone):
    """Zone for freeform notes and discussion."""

    def __init__(self):
        """Initialize the discussion zone."""
        super().__init__("Discussion")
        self.notes: List[Dict[str, Any]] = []

    async def handle_strokes(self, strokes: List[Stroke]) -> Dict[str, Any]:
        """Handle strokes for note-taking."""
        # All strokes in this zone are treated as notes
        note = {
            "id": f"note_{datetime.now().timestamp()}",
            "strokes": strokes,
            "timestamp": datetime.now().isoformat(),
            "text": "",  # Would be filled by handwriting recognition
        }

        self.notes.append(note)
        self.dirty = True

        return {"handled": True, "action": "added_note", "note": note}

    async def update(self):
        """Update discussion zone."""
        pass

    async def refresh(self):
        """Refresh discussion data."""
        pass

    def render(self) -> Dict[str, Any]:
        """Render the discussion area."""
        return {"type": "discussion", "notes": self.notes}

    def to_svg(self, width: int, height: int) -> str:
        """Convert discussion to SVG."""
        svg_parts = []

        # Render notes
        for note in self.notes:
            if note.get("text"):
                # Render as text
                svg_parts.append(
                    f'<text x="10" y="30" font-size="12">{note["text"]}</text>'
                )
            else:
                # Render strokes
                for stroke in note.get("strokes", []):
                    points = " ".join(f"{x},{y}" for x, y in stroke.points)
                    svg_parts.append(
                        f'<polyline points="{points}" fill="none" '
                        'stroke="black" stroke-width="1"/>'
                    )

        return "\n".join(svg_parts)

    async def generate_page(self) -> Dict[str, Any]:
        """Generate page for discussion."""
        return {"title": "Discussion & Notes", "content": self.render()}


class QuickActionsZone(BaseZone):
    """Zone for quick action buttons."""

    def __init__(self):
        """Initialize the quick actions zone."""
        super().__init__("Quick Actions")
        self.actions = [
            {"id": "new", "symbol": "⊕", "label": "New"},
            {"id": "assign", "symbol": "◈", "label": "Assign"},
            {"id": "sync", "symbol": "↻", "label": "Sync"},
            {"id": "run", "symbol": "⚡", "label": "Run"},
            {"id": "copy", "symbol": "📋", "label": "Copy"},
            {"id": "search", "symbol": "🔍", "label": "Search"},
            {"id": "stats", "symbol": "📊", "label": "Stats"},
            {"id": "config", "symbol": "⚙️", "label": "Config"},
        ]

    async def handle_strokes(self, strokes: List[Stroke]) -> Dict[str, Any]:
        """Handle strokes for action selection."""
        # Find which action was tapped
        position = strokes[0].start_point if strokes else (0, 0)
        action = self._find_action_at(position)

        if action:
            return {
                "handled": True,
                "action": "quick_action",
                "action_id": action["id"],
            }

        return {"handled": False}

    async def update(self):
        """Update quick actions."""
        pass

    async def refresh(self):
        """Refresh quick actions."""
        pass

    def render(self) -> Dict[str, Any]:
        """Render the quick actions."""
        return {"type": "quick_actions", "actions": self.actions}

    def to_svg(self, width: int, height: int) -> str:
        """Convert actions to SVG."""
        svg_parts = []

        # Calculate button spacing
        button_width = width // len(self.actions)

        for i, action in enumerate(self.actions):
            x = i * button_width

            # Button background
            svg_parts.append(
                f'<rect x="{x + 5}" y="10" width="{button_width - 10}" height="{height - 20}" '
                'fill="lightblue" stroke="black" stroke-width="1" rx="5"/>'
            )

            # Symbol
            svg_parts.append(
                f'<text x="{x + button_width // 2}" y="{height // 2}" '
                'text-anchor="middle" font-size="24">{action["symbol"]}</text>'
            )

            # Label
            svg_parts.append(
                f'<text x="{x + button_width // 2}" y="{height - 15}" '
                'text-anchor="middle" font-size="12">{action["label"]}</text>'
            )

        return "\n".join(svg_parts)

    async def generate_page(self) -> Dict[str, Any]:
        """Generate page for quick actions."""
        return {"title": "Quick Actions", "content": self.render()}

    def _find_action_at(self, position: Tuple[int, int]) -> Optional[Dict[str, Any]]:
        """Find which action was clicked."""
        x = position[0]
        button_width = 150  # Assuming 1200px width / 8 actions
        action_index = int(x // button_width)

        if 0 <= action_index < len(self.actions):
            return self.actions[action_index]

        return None
