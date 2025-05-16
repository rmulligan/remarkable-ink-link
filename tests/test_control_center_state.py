#!/usr/bin/env python3
"""Test the enhanced Control Center state management."""

import asyncio
import json
from datetime import datetime

import pytest

from src.inklink.control_center.state_manager import (
    ControlCenterState,
    StateEvent,
    StateEventType,
    StateSnapshot,
)


class TestControlCenterState:
    """Test suite for the Control Center state management."""

    @pytest.fixture
    def temp_state_file(self, tmp_path):
        """Create a temporary state file."""
        return tmp_path / "test_state.json"

    @pytest.fixture
    async def state_manager(self, temp_state_file):
        """Create a state manager instance."""
        state = ControlCenterState(persistence_path=str(temp_state_file))
        yield state
        # Cleanup
        if hasattr(state, "_save_timer") and state._save_timer:
            state._save_timer.cancel()

    @pytest.mark.asyncio
    async def test_zone_updates(self, state_manager):
        """Test zone state updates."""
        zone_id = "command_zone"
        zone_data = {
            "active": True,
            "content": ["command1", "command2"],
            "position": {"x": 100, "y": 200},
        }

        # Update zone
        await state_manager.update_zone(zone_id, zone_data)

        # Verify zone data
        zones = await state_manager.get_zones()
        assert zone_id in zones
        assert zones[zone_id] == zone_data

    @pytest.mark.asyncio
    async def test_canvas_updates(self, state_manager):
        """Test canvas state updates."""
        canvas_id = "main_canvas"
        canvas_data = {
            "width": 1920,
            "height": 1080,
            "active_tools": ["pen", "eraser"],
            "layers": ["layer1", "layer2"],
        }

        # Update canvas
        await state_manager.update_canvas(canvas_id, canvas_data)

        # Verify canvas data
        canvases = await state_manager.get_canvases()
        assert canvas_id in canvases
        assert canvases[canvas_id] == canvas_data

    @pytest.mark.asyncio
    async def test_agent_state(self, state_manager):
        """Test agent state management."""
        agent_id = "test_agent"
        agent_status = {
            "status": "running",
            "task": "process_handwriting",
            "started_at": datetime.now().isoformat(),
        }

        # Update agent state
        await state_manager.update_agent_state(agent_id, agent_status)

        # Verify agent state
        agents = await state_manager.get_agents()
        assert agent_id in agents
        assert agents[agent_id] == agent_status

    @pytest.mark.asyncio
    async def test_event_listeners(self, state_manager):
        """Test event listener registration and notification."""
        events_received = []

        async def event_handler(event: StateEvent):
            events_received.append(event)

        # Register listener
        state_manager.register_listener(StateEventType.ZONE_UPDATED, event_handler)

        # Update zone (should trigger event)
        await state_manager.update_zone("test_zone", {"active": True})

        # Wait for event processing
        await asyncio.sleep(0.1)

        # Verify event received
        assert len(events_received) == 1
        assert events_received[0].event_type == StateEventType.ZONE_UPDATED
        assert events_received[0].zone_id == "test_zone"

    @pytest.mark.asyncio
    async def test_state_persistence(self, state_manager, temp_state_file):
        """Test state persistence to file."""
        # Update some state
        await state_manager.update_zone("zone1", {"active": True})
        await state_manager.update_canvas("canvas1", {"width": 1920})

        # Force save
        await state_manager._save_state()

        # Verify file exists and contains data
        assert temp_state_file.exists()

        # Load saved state
        with open(temp_state_file, "r") as f:
            saved_data = json.load(f)

        assert "zones" in saved_data
        assert "canvases" in saved_data
        assert saved_data["zones"]["zone1"]["active"] is True
        assert saved_data["canvases"]["canvas1"]["width"] == 1920

    @pytest.mark.asyncio
    async def test_state_recovery(self, temp_state_file):
        """Test state recovery from persisted file."""
        # Create initial state and save it
        initial_state = {
            "zones": {"zone1": {"active": True}},
            "canvases": {"canvas1": {"width": 1920}},
            "agents": {"agent1": {"status": "idle"}},
            "tasks": {"task1": {"status": "completed"}},
            "settings": {"theme": "dark"},
            "version": 5,
        }

        with open(temp_state_file, "w") as f:
            json.dump(initial_state, f)

        # Create new state manager (should load from file)
        state_manager = ControlCenterState(persistence_path=str(temp_state_file))

        # Verify recovered state
        zones = await state_manager.get_zones()
        assert zones["zone1"]["active"] is True

        canvases = await state_manager.get_canvases()
        assert canvases["canvas1"]["width"] == 1920

        agents = await state_manager.get_agents()
        assert agents["agent1"]["status"] == "idle"

    @pytest.mark.asyncio
    async def test_create_snapshot(self, state_manager):
        """Test snapshot creation."""
        # Set up some state
        await state_manager.update_zone("zone1", {"active": True})
        await state_manager.update_settings({"theme": "dark"})

        # Create snapshot
        snapshot = await state_manager.create_snapshot()

        assert isinstance(snapshot, StateSnapshot)
        assert snapshot.zones["zone1"]["active"] is True
        assert snapshot.settings["theme"] == "dark"
        assert snapshot.version > 0
        assert isinstance(snapshot.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_task_lifecycle(self, state_manager):
        """Test task state lifecycle."""
        task_id = "test_task"
        task_data = {
            "type": "handwriting_recognition",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }

        # Add task
        await state_manager.add_task(task_id, task_data)

        # Update task status
        await state_manager.update_task_status(task_id, "running")

        # Complete task
        await state_manager.complete_task(task_id, {"result": "success"})

        # Verify task state
        tasks = await state_manager.get_tasks()
        assert tasks[task_id]["status"] == "completed"
        assert tasks[task_id]["result"] == "success"
        assert "completed_at" in tasks[task_id]

    @pytest.mark.asyncio
    async def test_event_type_filtering(self, state_manager):
        """Test that listeners only receive events of registered types."""
        zone_events = []
        canvas_events = []

        async def zone_handler(event: StateEvent):
            zone_events.append(event)

        async def canvas_handler(event: StateEvent):
            canvas_events.append(event)

        # Register listeners for different event types
        state_manager.register_listener(StateEventType.ZONE_UPDATED, zone_handler)
        state_manager.register_listener(StateEventType.CANVAS_UPDATED, canvas_handler)

        # Trigger different events
        await state_manager.update_zone("zone1", {"active": True})
        await state_manager.update_canvas("canvas1", {"width": 1920})

        # Wait for event processing
        await asyncio.sleep(0.1)

        # Verify correct filtering
        assert len(zone_events) == 1
        assert len(canvas_events) == 1
        assert zone_events[0].event_type == StateEventType.ZONE_UPDATED
        assert canvas_events[0].event_type == StateEventType.CANVAS_UPDATED

    @pytest.mark.asyncio
    async def test_thread_safety(self, state_manager):
        """Test thread-safe operations."""
        update_count = 100
        zone_id = "concurrent_zone"

        async def update_zone(i):
            await state_manager.update_zone(zone_id, {"count": i})

        # Create concurrent updates
        tasks = [update_zone(i) for i in range(update_count)]
        await asyncio.gather(*tasks)

        # Verify final state
        zones = await state_manager.get_zones()
        assert zone_id in zones
        # The last update should win
        assert zones[zone_id]["count"] in range(update_count)
