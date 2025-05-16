"""Dynamic canvas system for the control center."""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .zones import BaseZone


@dataclass
class CanvasPosition:
    """Represents a position on the canvas."""

    x: int
    y: int

    def __add__(self, other: "CanvasPosition") -> "CanvasPosition":
        return CanvasPosition(self.x + other.x, self.y + other.y)

    def in_bounds(self, pos: Tuple[int, int], size: Tuple[int, int]) -> bool:
        """Check if this position is within bounds."""
        return (
            pos[0] <= self.x <= pos[0] + size[0]
            and pos[1] <= self.y <= pos[1] + size[1]
        )


@dataclass
class CanvasZone:
    """Represents a zone on the canvas."""

    id: str
    zone: BaseZone
    position: Tuple[int, int]
    size: Tuple[int, int]
    visible: bool = True
    interactive: bool = True


class DynamicCanvas:
    """Dynamic canvas that manages zones and interactions."""

    def __init__(self, width: int = 1200, height: int = 600):
        """Initialize the canvas."""
        self.width = width
        self.height = height
        self.zones: Dict[str, CanvasZone] = {}
        self.active_zone: Optional[str] = None
        self.dirty = True  # Needs redraw
        self.layout_engine = LayoutEngine()

    def add_zone(
        self,
        zone_id: str,
        zone: BaseZone,
        position: Tuple[int, int],
        size: Tuple[int, int],
    ):
        """Add a zone to the canvas."""
        self.zones[zone_id] = CanvasZone(
            id=zone_id, zone=zone, position=position, size=size
        )
        self.dirty = True

    def remove_zone(self, zone_id: str):
        """Remove a zone from the canvas."""
        if zone_id in self.zones:
            del self.zones[zone_id]
            self.dirty = True

    def get_zone(self, zone_id: str) -> Optional[BaseZone]:
        """Get a zone by ID."""
        canvas_zone = self.zones.get(zone_id)
        return canvas_zone.zone if canvas_zone else None

    def find_zone_at_position(self, position: Tuple[int, int]) -> Optional[str]:
        """Find which zone contains the given position."""
        pos = CanvasPosition(position[0], position[1])

        for zone_id, canvas_zone in self.zones.items():
            if canvas_zone.visible and canvas_zone.interactive:
                if pos.in_bounds(canvas_zone.position, canvas_zone.size):
                    return zone_id

        return None

    def move_zone(self, zone_id: str, new_position: Tuple[int, int]):
        """Move a zone to a new position."""
        if zone_id in self.zones:
            self.zones[zone_id].position = new_position
            self.dirty = True

    def resize_zone(self, zone_id: str, new_size: Tuple[int, int]):
        """Resize a zone."""
        if zone_id in self.zones:
            self.zones[zone_id].size = new_size
            self.dirty = True

    def set_zone_visibility(self, zone_id: str, visible: bool):
        """Set zone visibility."""
        if zone_id in self.zones:
            self.zones[zone_id].visible = visible
            self.dirty = True

    def set_zone_interactivity(self, zone_id: str, interactive: bool):
        """Set zone interactivity."""
        if zone_id in self.zones:
            self.zones[zone_id].interactive = interactive

    async def update(self):
        """Update all zones."""
        # Update each zone
        for canvas_zone in self.zones.values():
            if canvas_zone.visible:
                await canvas_zone.zone.update()

        self.dirty = True

    async def refresh(self):
        """Force a complete refresh of the canvas."""
        # Refresh each zone
        for canvas_zone in self.zones.values():
            await canvas_zone.zone.refresh()

        self.dirty = True

    def layout(self, layout_type: str = "grid"):
        """Apply a layout to all zones."""
        self.layout_engine.apply_layout(self.zones, layout_type)
        self.dirty = True

    def render(self) -> Dict[str, Any]:
        """Render the canvas to a format suitable for display."""
        if not self.dirty:
            return self._last_render

        render_data = {"width": self.width, "height": self.height, "zones": []}

        # Render each visible zone
        for zone_id, canvas_zone in self.zones.items():
            if canvas_zone.visible:
                zone_render = canvas_zone.zone.render()
                render_data["zones"].append(
                    {
                        "id": zone_id,
                        "position": canvas_zone.position,
                        "size": canvas_zone.size,
                        "content": zone_render,
                    }
                )

        self._last_render = render_data
        self.dirty = False
        return render_data

    def to_svg(self) -> str:
        """Convert canvas to SVG format."""
        svg_parts = [
            f'<svg width="{self.width}" height="{self.height}" '
            'xmlns="http://www.w3.org/2000/svg">'
        ]

        # Add background
        svg_parts.append(
            f'<rect width="{self.width}" height="{self.height}" ' 'fill="white"/>'
        )

        # Render each zone
        for zone_id, canvas_zone in self.zones.items():
            if canvas_zone.visible:
                x, y = canvas_zone.position
                w, h = canvas_zone.size

                # Zone container
                svg_parts.append(f'<g transform="translate({x},{y})">')

                # Zone border
                svg_parts.append(
                    f'<rect width="{w}" height="{h}" '
                    'fill="none" stroke="black" stroke-width="1"/>'
                )

                # Zone content
                zone_svg = canvas_zone.zone.to_svg(w, h)
                svg_parts.append(zone_svg)

                svg_parts.append("</g>")

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)


class LayoutEngine:
    """Handles automatic layout of zones."""

    def apply_layout(self, zones: Dict[str, CanvasZone], layout_type: str):
        """Apply a layout algorithm to the zones."""
        if layout_type == "grid":
            self._apply_grid_layout(zones)
        elif layout_type == "flow":
            self._apply_flow_layout(zones)
        elif layout_type == "stack":
            self._apply_stack_layout(zones)

    def _apply_grid_layout(self, zones: Dict[str, CanvasZone]):
        """Apply a grid layout."""
        visible_zones = [z for z in zones.values() if z.visible]
        if not visible_zones:
            return

        # Calculate grid dimensions
        count = len(visible_zones)
        cols = int(count**0.5) + 1
        rows = (count + cols - 1) // cols

        # Calculate cell size
        canvas_width = 1200  # Default canvas size
        canvas_height = 600
        cell_width = canvas_width // cols
        cell_height = canvas_height // rows

        # Position zones
        for i, zone in enumerate(visible_zones):
            row = i // cols
            col = i % cols
            zone.position = (col * cell_width, row * cell_height)
            zone.size = (cell_width - 10, cell_height - 10)  # Add padding

    def _apply_flow_layout(self, zones: Dict[str, CanvasZone]):
        """Apply a flow layout (left to right, top to bottom)."""
        visible_zones = [z for z in zones.values() if z.visible]
        if not visible_zones:
            return

        x, y = 10, 10  # Starting position
        max_height = 0
        row_width = 0
        max_width = 1200  # Canvas width

        for zone in visible_zones:
            # Check if we need to wrap to next row
            if row_width + zone.size[0] > max_width:
                x = 10
                y += max_height + 10
                max_height = 0
                row_width = 0

            # Position zone
            zone.position = (x, y)

            # Update positions
            x += zone.size[0] + 10
            row_width += zone.size[0] + 10
            max_height = max(max_height, zone.size[1])

    def _apply_stack_layout(self, zones: Dict[str, CanvasZone]):
        """Apply a vertical stack layout."""
        visible_zones = [z for z in zones.values() if z.visible]
        if not visible_zones:
            return

        y = 10
        for zone in visible_zones:
            zone.position = (10, y)
            zone.size = (1180, zone.size[1])  # Full width
            y += zone.size[1] + 10
