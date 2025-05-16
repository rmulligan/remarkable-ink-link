#!/usr/bin/env python3
"""Test the enhanced Control Center implementation."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.inklink.control_center.core_enhanced import EnhancedInkControlCenter
from src.inklink.control_center.state_manager import StateEventType


class TestEnhancedControlCenter:
    """Test suite for the enhanced Control Center."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        remarkable_service = Mock()
        handwriting_service = Mock()
        agent_manager = Mock()
        return remarkable_service, handwriting_service, agent_manager

    @pytest.fixture
    async def control_center(self, mock_services, tmp_path):
        """Create an enhanced control center instance."""
        remarkable_service, handwriting_service, agent_manager = mock_services
        state_file = tmp_path / "test_state.json"

        center = EnhancedInkControlCenter(
            remarkable_service,
            handwriting_service,
            agent_manager,
            state_file=str(state_file),
        )

        # Initialize the control center
        await center.initialize()

        yield center

        # Cleanup
        if hasattr(center.state, "_save_timer") and center.state._save_timer:
            center.state._save_timer.cancel()

    @pytest.mark.asyncio
    async def test_initialization(self, control_center):
        """Test control center initialization."""
        # Verify state is initialized
        zones = await control_center.state.get_zones()
        assert len(zones) > 0  # Should have zones after initialization

        # Verify event handlers are set up
        assert control_center._event_handlers is not None

    @pytest.mark.asyncio
    async def test_process_ink_with_state(self, control_center):
        """Test ink processing with state tracking."""
        # Mock ink data
        ink_data = {"strokes": [{"points": [(0, 0), (10, 10)]}]}
        zone_id = "command_zone"

        # Mock the processor
        control_center.processor = Mock()
        control_center.processor.process = AsyncMock(
            return_value={"type": "command", "content": "test command"}
        )

        # Process ink
        await control_center.process_ink(ink_data, zone_id)

        # Verify state was updated
        zones = await control_center.state.get_zones()
        assert zone_id in zones
        assert "last_activity" in zones[zone_id]

        # Verify task was created and tracked
        tasks = await control_center.state.get_tasks()
        assert len(tasks) > 0

    @pytest.mark.asyncio
    async def test_agent_execution_with_state(self, control_center):
        """Test agent execution with state tracking."""
        # Mock agent
        mock_agent = Mock()
        mock_agent.execute = AsyncMock(return_value={"result": "success"})

        control_center.agent_manager.get_agent = Mock(return_value=mock_agent)

        # Execute agent
        agent_id = "test_agent"
        task_data = {"action": "test"}

        await control_center.execute_agent(agent_id, task_data)

        # Verify agent state was tracked
        agents = await control_center.state.get_agents()
        assert agent_id in agents
        assert agents[agent_id]["status"] == "idle"

        # Verify task was tracked
        tasks = await control_center.state.get_tasks()
        task_found = False
        for task in tasks.values():
            if task.get("agent_id") == agent_id:
                task_found = True
                assert task["status"] == "completed"
                break
        assert task_found

    @pytest.mark.asyncio
    async def test_error_handling_with_state(self, control_center):
        """Test error handling and state updates."""
        # Mock a failing processor
        control_center.processor = Mock()
        control_center.processor.process = AsyncMock(
            side_effect=Exception("Processing error")
        )

        # Process ink (should fail gracefully)
        ink_data = {"strokes": []}
        zone_id = "test_zone"

        result = await control_center.process_ink(ink_data, zone_id)

        # Verify error was handled
        assert result is not None  # Should have some error result

        # Verify task was marked as failed
        tasks = await control_center.state.get_tasks()
        failed_task = None
        for task in tasks.values():
            if task.get("zone_id") == zone_id and task["status"] == "failed":
                failed_task = task
                break

        assert failed_task is not None
        assert "error" in failed_task

    @pytest.mark.asyncio
    async def test_state_recovery(self, mock_services, tmp_path):
        """Test state recovery from persisted data."""
        remarkable_service, handwriting_service, agent_manager = mock_services
        state_file = tmp_path / "test_state.json"

        # Create initial control center and add some state
        center1 = EnhancedInkControlCenter(
            remarkable_service,
            handwriting_service,
            agent_manager,
            state_file=str(state_file),
        )
        await center1.initialize()

        # Add some state
        await center1.state.update_zone("zone1", {"active": True})
        await center1.state.update_settings({"theme": "dark"})

        # Force save
        await center1.state._save_state()

        # Create new control center (should recover state)
        center2 = EnhancedInkControlCenter(
            remarkable_service,
            handwriting_service,
            agent_manager,
            state_file=str(state_file),
        )
        await center2.initialize()

        # Wait for recovery
        await asyncio.sleep(0.1)

        # Verify state was recovered
        zones = await center2.state.get_zones()
        assert "zone1" in zones
        assert zones["zone1"]["active"] is True

        settings = await center2.state.get_settings()
        assert settings["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_event_driven_updates(self, control_center):
        """Test event-driven state updates."""
        events_received = []

        async def event_handler(event):
            events_received.append(event)

        # Register listener
        control_center.state.register_listener(
            StateEventType.ZONE_UPDATED, event_handler
        )

        # Update zone through control center
        zone_id = "test_zone"
        zone_data = {"active": True}
        await control_center._update_zone_state(zone_id, zone_data)

        # Wait for event processing
        await asyncio.sleep(0.1)

        # Verify event was received
        assert len(events_received) == 1
        assert events_received[0].zone_id == zone_id

    @pytest.mark.asyncio
    async def test_canvas_operations(self, control_center):
        """Test canvas operations with state tracking."""
        canvas_id = "main_canvas"
        canvas_data = {"width": 1920, "height": 1080, "active_tools": ["pen"]}

        # Update canvas
        await control_center._update_canvas_state(canvas_id, canvas_data)

        # Verify state
        canvases = await control_center.state.get_canvases()
        assert canvas_id in canvases
        assert canvases[canvas_id]["width"] == 1920

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, control_center):
        """Test concurrent operations on the control center."""
        # Mock processor for concurrent testing
        control_center.processor = Mock()
        control_center.processor.process = AsyncMock(
            return_value={"type": "text", "content": "test"}
        )

        # Create multiple concurrent ink processing tasks
        tasks = []
        for i in range(10):
            ink_data = {"strokes": [{"id": f"stroke_{i}"}]}
            zone_id = f"zone_{i % 3}"  # Use 3 different zones
            task = control_center.process_ink(ink_data, zone_id)
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks)

        # Verify all completed
        assert len(results) == 10

        # Verify state consistency
        zones = await control_center.state.get_zones()
        for i in range(3):
            zone_id = f"zone_{i}"
            assert zone_id in zones
            assert "last_activity" in zones[zone_id]
