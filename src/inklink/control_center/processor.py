"""Ink processing and command parsing."""

import asyncio
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)


@dataclass
class Stroke:
    """Represents a single ink stroke."""

    points: List[Tuple[float, float]]
    pressure: List[float]
    timestamp: float

    @property
    def start_point(self) -> Tuple[float, float]:
        """Get the starting point of the stroke."""
        return self.points[0] if self.points else (0, 0)

    @property
    def end_point(self) -> Tuple[float, float]:
        """Get the ending point of the stroke."""
        return self.points[-1] if self.points else (0, 0)

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Get the bounding box of the stroke."""
        if not self.points:
            return (0, 0, 0, 0)

        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return (min(xs), min(ys), max(xs), max(ys))


class GestureType(Enum):
    """Types of gestures that can be detected."""

    CIRCLE = "circle"
    ARROW = "arrow"
    CROSS_OUT = "cross_out"
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    BOX = "box"
    UNDERLINE = "underline"
    QUESTION_MARK = "question_mark"


@dataclass
class Gesture:
    """Represents a detected gesture."""

    type: GestureType
    bounds: Tuple[float, float, float, float]
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class CommandType(Enum):
    """Types of commands that can be executed."""

    AGENT_INSTRUCTION = "agent_instruction"
    CREATE_TASK = "create_task"
    ASSIGN_TASK = "assign_task"
    COMPLETE_TASK = "complete_task"
    MOVE_TASK = "move_task"
    TAG_ITEM = "tag_item"
    PRIORITY_MARK = "priority_mark"
    QUICK_ACTION = "quick_action"
    QUERY_STATUS = "query_status"


@dataclass
class InkCommand:
    """Represents a command parsed from ink input."""

    type: CommandType
    target: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    source_text: Optional[str] = None
    source_gesture: Optional[Gesture] = None


class InkProcessor:
    """Processes handwritten input and detects gestures/commands."""

    def __init__(self, handwriting_service: HandwritingRecognitionService):
        """Initialize the ink processor."""
        self.handwriting_service = handwriting_service
        self.gesture_detector = GestureDetector()
        self.command_parser = CommandParser()

    async def detect_gestures(self, strokes: List[Stroke]) -> List[Gesture]:
        """Detect gestures from ink strokes."""
        return self.gesture_detector.detect(strokes)

    async def recognize_text(self, strokes: List[Stroke]) -> str:
        """Convert handwriting to text."""
        # Convert strokes to format expected by handwriting service
        ink_data = self._strokes_to_ink_data(strokes)

        # Recognize text
        result = await self.handwriting_service.recognize_text(ink_data)
        return result.get("text", "")

    def parse_commands(self, text: str, gestures: List[Gesture]) -> List[InkCommand]:
        """Parse commands from text and gestures."""
        commands = []

        # Parse text-based commands
        text_commands = self.command_parser.parse_text(text)
        commands.extend(text_commands)

        # Parse gesture-based commands
        gesture_commands = self.command_parser.parse_gestures(gestures)
        commands.extend(gesture_commands)

        return commands

    def _strokes_to_ink_data(self, strokes: List[Stroke]) -> Dict[str, Any]:
        """Convert strokes to format for handwriting recognition."""
        return {
            "strokes": [
                {
                    "points": stroke.points,
                    "pressure": stroke.pressure,
                    "timestamp": stroke.timestamp,
                }
                for stroke in strokes
            ]
        }


class GestureDetector:
    """Detects gestures from ink strokes."""

    def detect(self, strokes: List[Stroke]) -> List[Gesture]:
        """Detect all gestures from strokes."""
        gestures = []

        # Single stroke gestures
        if len(strokes) == 1:
            stroke = strokes[0]

            # Circle detection
            if self._is_circle(stroke):
                gestures.append(
                    Gesture(
                        type=GestureType.CIRCLE, bounds=stroke.bounds, confidence=0.9
                    )
                )

            # Question mark detection
            elif self._is_question_mark(stroke):
                gestures.append(
                    Gesture(
                        type=GestureType.QUESTION_MARK,
                        bounds=stroke.bounds,
                        confidence=0.85,
                    )
                )

            # Arrow detection
            elif self._is_arrow(stroke):
                gestures.append(
                    Gesture(
                        type=GestureType.ARROW,
                        bounds=stroke.bounds,
                        confidence=0.9,
                        metadata={"start": stroke.start_point, "end": stroke.end_point},
                    )
                )

        # Multi-stroke gestures
        elif len(strokes) == 2:
            # Cross-out detection
            if self._is_cross_out(strokes):
                combined_bounds = self._combine_bounds([s.bounds for s in strokes])
                gestures.append(
                    Gesture(
                        type=GestureType.CROSS_OUT,
                        bounds=combined_bounds,
                        confidence=0.85,
                    )
                )

        # Box detection (4 strokes)
        elif len(strokes) == 4:
            if self._is_box(strokes):
                combined_bounds = self._combine_bounds([s.bounds for s in strokes])
                gestures.append(
                    Gesture(
                        type=GestureType.BOX, bounds=combined_bounds, confidence=0.9
                    )
                )

        return gestures

    def _is_circle(self, stroke: Stroke) -> bool:
        """Check if stroke is a circle."""
        if len(stroke.points) < 10:
            return False

        # Check if start and end points are close
        start = stroke.start_point
        end = stroke.end_point
        distance = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5

        # Check if the path is roughly circular
        bounds = stroke.bounds
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        aspect_ratio = width / height if height > 0 else 1

        return (
            distance < width * 0.2 and 0.8 < aspect_ratio < 1.2  # Start/end are close
        )  # Roughly square bounds

    def _is_arrow(self, stroke: Stroke) -> bool:
        """Check if stroke is an arrow."""
        if len(stroke.points) < 5:
            return False

        # Simple heuristic: straight line with sharp turn at end
        # More sophisticated detection would analyze angle changes
        points = stroke.points

        # Check if mostly straight
        start, end = points[0], points[-1]

        # Calculate linearity
        line_dist = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
        path_dist = sum(
            (
                (points[i + 1][0] - points[i][0]) ** 2
                + (points[i + 1][1] - points[i][1]) ** 2
            )
            ** 0.5
            for i in range(len(points) - 1)
        )

        linearity = line_dist / path_dist if path_dist > 0 else 0
        return linearity > 0.8

    def _is_cross_out(self, strokes: List[Stroke]) -> bool:
        """Check if strokes form a cross-out."""
        if len(strokes) != 2:
            return False

        # Check if strokes intersect and are roughly perpendicular
        # Simplified check - would need more sophisticated line intersection
        bounds1 = strokes[0].bounds
        bounds2 = strokes[1].bounds

        # Check if bounding boxes overlap
        return (
            bounds1[0] < bounds2[2]
            and bounds2[0] < bounds1[2]
            and bounds1[1] < bounds2[3]
            and bounds2[1] < bounds1[3]
        )

    def _is_box(self, strokes: List[Stroke]) -> bool:
        """Check if strokes form a box."""
        if len(strokes) != 4:
            return False

        # Simplified check - would need to verify strokes form rectangle
        # Check if strokes connect to form closed shape
        return True  # Placeholder

    def _is_question_mark(self, stroke: Stroke) -> bool:
        """Check if stroke is a question mark."""
        # Simplified - would need shape analysis
        points = stroke.points
        if len(points) < 10:
            return False

        # Check for characteristic curve and dot
        return False  # Placeholder

    def _combine_bounds(
        self, bounds_list: List[Tuple[float, float, float, float]]
    ) -> Tuple[float, float, float, float]:
        """Combine multiple bounds into one."""
        if not bounds_list:
            return (0, 0, 0, 0)

        min_x = min(b[0] for b in bounds_list)
        min_y = min(b[1] for b in bounds_list)
        max_x = max(b[2] for b in bounds_list)
        max_y = max(b[3] for b in bounds_list)

        return (min_x, min_y, max_x, max_y)


class CommandParser:
    """Parses commands from text and gestures."""

    # Command patterns
    AGENT_COMMAND = re.compile(r"@Agent\[(\w+)\]:\s*(.*)")
    TAG_PATTERN = re.compile(r"#(\w+)")
    PRIORITY_PATTERN = re.compile(r"!(\w+)")
    TASK_PATTERN = re.compile(r"^\s*-\s+(.+)")  # Markdown list item

    def parse_text(self, text: str) -> List[InkCommand]:
        """Parse commands from text."""
        commands = []

        # Check for agent commands
        if match := self.AGENT_COMMAND.match(text):
            agent_name, instruction = match.groups()
            commands.append(
                InkCommand(
                    type=CommandType.AGENT_INSTRUCTION,
                    target=agent_name,
                    parameters={"instruction": instruction},
                    source_text=text,
                )
            )

        # Check for task creation
        elif match := self.TASK_PATTERN.match(text):
            task_text = match.group(1)

            # Extract tags
            tags = self.TAG_PATTERN.findall(task_text)

            # Extract priority
            priority_match = self.PRIORITY_PATTERN.search(task_text)
            priority = priority_match.group(1) if priority_match else "normal"

            # Clean task text
            clean_text = self.TAG_PATTERN.sub("", task_text)
            clean_text = self.PRIORITY_PATTERN.sub("", clean_text).strip()

            commands.append(
                InkCommand(
                    type=CommandType.CREATE_TASK,
                    parameters={
                        "title": clean_text,
                        "tags": tags,
                        "priority": priority,
                    },
                    source_text=text,
                )
            )

        # Check for tags (for existing items)
        elif tags := self.TAG_PATTERN.findall(text):
            commands.append(
                InkCommand(
                    type=CommandType.TAG_ITEM,
                    parameters={"tags": tags},
                    source_text=text,
                )
            )

        # Check for priority marking
        elif match := self.PRIORITY_PATTERN.match(text):
            priority = match.group(1)
            commands.append(
                InkCommand(
                    type=CommandType.PRIORITY_MARK,
                    parameters={"priority": priority},
                    source_text=text,
                )
            )

        return commands

    def parse_gestures(self, gestures: List[Gesture]) -> List[InkCommand]:
        """Parse commands from gestures."""
        commands = []

        for gesture in gestures:
            if gesture.type == GestureType.ARROW:
                # Arrow indicates assignment or movement
                commands.append(
                    InkCommand(
                        type=CommandType.ASSIGN_TASK,
                        parameters={
                            "from_position": gesture.metadata.get("start"),
                            "to_position": gesture.metadata.get("end"),
                        },
                        source_gesture=gesture,
                    )
                )

            elif gesture.type == GestureType.CROSS_OUT:
                # Cross-out indicates completion
                commands.append(
                    InkCommand(
                        type=CommandType.COMPLETE_TASK,
                        parameters={"bounds": gesture.bounds},
                        source_gesture=gesture,
                    )
                )

            elif gesture.type == GestureType.QUESTION_MARK:
                # Question mark queries status
                commands.append(
                    InkCommand(
                        type=CommandType.QUERY_STATUS,
                        parameters={"bounds": gesture.bounds},
                        source_gesture=gesture,
                    )
                )

            elif gesture.type == GestureType.BOX:
                # Box creates new item or groups items
                commands.append(
                    InkCommand(
                        type=CommandType.CREATE_TASK,
                        parameters={"bounds": gesture.bounds},
                        source_gesture=gesture,
                    )
                )

        return commands
