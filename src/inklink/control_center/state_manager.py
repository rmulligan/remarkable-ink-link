"""Enhanced state management for the Control Center.

This module provides thread-safe state management with persistence,
event notifications, and recovery capabilities.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger(__name__)


class StateEventType(Enum):
    """Types of state change events."""

    ZONE_UPDATED = "zone_updated"
    ELEMENT_ADDED = "element_added"
    ELEMENT_REMOVED = "element_removed"
    ELEMENT_UPDATED = "element_updated"
    SELECTION_CHANGED = "selection_changed"
    GESTURE_DETECTED = "gesture_detected"
    COMMAND_EXECUTED = "command_executed"
    SYNC_STARTED = "sync_started"
    SYNC_COMPLETED = "sync_completed"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class StateEvent:
    """Represents a state change event."""

    event_type: StateEventType
    timestamp: datetime
    zone_id: Optional[str] = None
    element_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class StateSnapshot:
    """Represents a complete state snapshot."""

    timestamp: datetime
    version: int
    zones: Dict[str, Dict[str, Any]]
    selections: List[str]
    active_gestures: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class ControlCenterState:
    """Thread-safe state manager for the Control Center."""

    def __init__(self, persistence_path: Optional[Path] = None):
        """Initialize the state manager."""
        self.persistence_path = persistence_path
        self._version = 0
        self._lock = asyncio.Lock()

        # State containers
        self._zones: Dict[str, Dict[str, Any]] = {}
        self._selections: Set[str] = set()
        self._active_gestures: List[Dict[str, Any]] = []
        self._metadata: Dict[str, Any] = {}

        # Event handling
        self._event_listeners: Dict[StateEventType, List[Callable]] = {
            event_type: [] for event_type in StateEventType
        }
        self._event_history: List[StateEvent] = []
        self._max_history_size = 1000

        # Load persisted state if available
        if self.persistence_path and self.persistence_path.exists():
            self._load_state()

    async def update_zone(
        self, zone_id: str, zone_data: Dict[str, Any], notify: bool = True
    ) -> None:
        """Update a zone's state."""
        async with self._lock:
            self._zones[zone_id] = zone_data
            self._version += 1

            if notify:
                event = StateEvent(
                    event_type=StateEventType.ZONE_UPDATED,
                    timestamp=datetime.now(),
                    zone_id=zone_id,
                    data={"zone_data": zone_data},
                )
                await self._emit_event(event)

            # Persist state
            await self._save_state()

    async def get_zone(self, zone_id: str) -> Optional[Dict[str, Any]]:
        """Get a zone's current state."""
        async with self._lock:
            return self._zones.get(zone_id)

    async def add_element(
        self, zone_id: str, element_id: str, element_data: Dict[str, Any]
    ) -> None:
        """Add an element to a zone."""
        async with self._lock:
            if zone_id not in self._zones:
                self._zones[zone_id] = {"elements": {}}

            if "elements" not in self._zones[zone_id]:
                self._zones[zone_id]["elements"] = {}

            self._zones[zone_id]["elements"][element_id] = element_data
            self._version += 1

            event = StateEvent(
                event_type=StateEventType.ELEMENT_ADDED,
                timestamp=datetime.now(),
                zone_id=zone_id,
                element_id=element_id,
                data={"element_data": element_data},
            )
            await self._emit_event(event)
            await self._save_state()

    async def remove_element(self, zone_id: str, element_id: str) -> None:
        """Remove an element from a zone."""
        async with self._lock:
            if (
                zone_id in self._zones
                and "elements" in self._zones[zone_id]
                and element_id in self._zones[zone_id]["elements"]
            ):

                del self._zones[zone_id]["elements"][element_id]
                self._version += 1

                event = StateEvent(
                    event_type=StateEventType.ELEMENT_REMOVED,
                    timestamp=datetime.now(),
                    zone_id=zone_id,
                    element_id=element_id,
                )
                await self._emit_event(event)
                await self._save_state()

    async def update_element(
        self, zone_id: str, element_id: str, element_data: Dict[str, Any]
    ) -> None:
        """Update an element in a zone."""
        async with self._lock:
            if (
                zone_id in self._zones
                and "elements" in self._zones[zone_id]
                and element_id in self._zones[zone_id]["elements"]
            ):

                self._zones[zone_id]["elements"][element_id].update(element_data)
                self._version += 1

                event = StateEvent(
                    event_type=StateEventType.ELEMENT_UPDATED,
                    timestamp=datetime.now(),
                    zone_id=zone_id,
                    element_id=element_id,
                    data={"element_data": element_data},
                )
                await self._emit_event(event)
                await self._save_state()

    async def update_selection(self, selected_items: List[str]) -> None:
        """Update the current selection."""
        async with self._lock:
            old_selection = set(self._selections)
            self._selections = set(selected_items)

            if old_selection != self._selections:
                self._version += 1

                event = StateEvent(
                    event_type=StateEventType.SELECTION_CHANGED,
                    timestamp=datetime.now(),
                    data={
                        "old_selection": list(old_selection),
                        "new_selection": list(self._selections),
                    },
                )
                await self._emit_event(event)
                await self._save_state()

    async def get_selection(self) -> List[str]:
        """Get the current selection."""
        async with self._lock:
            return list(self._selections)

    async def add_gesture(self, gesture_data: Dict[str, Any]) -> None:
        """Add an active gesture."""
        async with self._lock:
            self._active_gestures.append(gesture_data)
            self._version += 1

            event = StateEvent(
                event_type=StateEventType.GESTURE_DETECTED,
                timestamp=datetime.now(),
                data={"gesture": gesture_data},
            )
            await self._emit_event(event)

    async def clear_gestures(self) -> None:
        """Clear all active gestures."""
        async with self._lock:
            self._active_gestures.clear()
            self._version += 1

    async def get_snapshot(self) -> StateSnapshot:
        """Get a complete snapshot of the current state."""
        async with self._lock:
            return StateSnapshot(
                timestamp=datetime.now(),
                version=self._version,
                zones=dict(self._zones),
                selections=list(self._selections),
                active_gestures=list(self._active_gestures),
                metadata=dict(self._metadata),
            )

    async def restore_snapshot(self, snapshot: StateSnapshot) -> None:
        """Restore state from a snapshot."""
        async with self._lock:
            self._zones = snapshot.zones
            self._selections = set(snapshot.selections)
            self._active_gestures = snapshot.active_gestures
            self._metadata = snapshot.metadata
            self._version = snapshot.version + 1

            await self._save_state()

    def add_event_listener(
        self, event_type: StateEventType, callback: Callable[[StateEvent], None]
    ) -> None:
        """Add an event listener."""
        self._event_listeners[event_type].append(callback)

    def remove_event_listener(
        self, event_type: StateEventType, callback: Callable[[StateEvent], None]
    ) -> None:
        """Remove an event listener."""
        if callback in self._event_listeners[event_type]:
            self._event_listeners[event_type].remove(callback)

    async def _emit_event(self, event: StateEvent) -> None:
        """Emit an event to all listeners."""
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)

        # Notify listeners
        for callback in self._event_listeners[event.event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in event listener: {e}")

                # Emit error event
                if event.event_type != StateEventType.ERROR_OCCURRED:
                    error_event = StateEvent(
                        event_type=StateEventType.ERROR_OCCURRED,
                        timestamp=datetime.now(),
                        error=str(e),
                        data={"original_event": asdict(event)},
                    )
                    await self._emit_event(error_event)

    async def _save_state(self) -> None:
        """Persist the current state to disk."""
        if not self.persistence_path:
            return

        try:
            snapshot = await self.get_snapshot()
            state_data = {
                "timestamp": snapshot.timestamp.isoformat(),
                "version": snapshot.version,
                "zones": snapshot.zones,
                "selections": snapshot.selections,
                "active_gestures": snapshot.active_gestures,
                "metadata": snapshot.metadata,
            }

            # Create directory if it doesn't exist
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temporary file first
            temp_path = self.persistence_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump(state_data, f, indent=2)

            # Atomic rename
            temp_path.replace(self.persistence_path)

        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _load_state(self) -> None:
        """Load persisted state from disk."""
        if not self.persistence_path or not self.persistence_path.exists():
            return

        try:
            with open(self.persistence_path, "r") as f:
                state_data = json.load(f)

            self._zones = state_data.get("zones", {})
            self._selections = set(state_data.get("selections", []))
            self._active_gestures = state_data.get("active_gestures", [])
            self._metadata = state_data.get("metadata", {})
            self._version = state_data.get("version", 0)

            logger.info(f"Loaded state from {self.persistence_path}")

        except Exception as e:
            logger.error(f"Failed to load state: {e}")
