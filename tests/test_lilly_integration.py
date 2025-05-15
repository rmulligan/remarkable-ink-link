"""Integration test for the Lilly persona with Claude Vision."""

import os
import json
import pytest
from unittest.mock import patch, MagicMock, mock_open

from inklink.adapters.claude_vision_adapter import ClaudeVisionAdapter
from inklink.adapters.handwriting_adapter import HandwritingAdapter
from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)
from inklink.config import get_config


# Sample content that would be in the persona file
SAMPLE_PERSONA = """# Lilly: reMarkable Companion

## Core Responsibilities
- Process handwritten notes and respond thoughtfully
- Extract knowledge and entities to build a knowledge graph
- Maintain conversation history and context
- Handle tagged commands like #summarize, #task, etc.

## Voice and Tone
- Friendly, insightful, and helpful
- Concise and clear communication
- Professional with a touch of warmth
"""

# Sample workflow examples
SAMPLE_WORKFLOWS = """# Example Workflows

## Tag Processing

### #summarize Tag
When you see #summarize, create a concise summary of the content.

**Example:**
Input: "Meeting notes from project review #summarize"
Response: "Here's a summary of your meeting notes: [summary points]"

### #task Tag
When you see #task, extract actionable items and create a task list.

**Example:**
Input: "Product roadmap discussion #task"
Response: "I've extracted these tasks from your notes: [bulleted task list]"
"""

# Mock subprocess response from Claude CLI
MOCK_CLAUDE_RESPONSE = {
    "content": [
        {
            "type": "text",
            "text": "I've analyzed your handwritten notes about the project timeline. Here are the key points:\n\n1. Project kickoff scheduled for June 15th\n2. Three main phases identified: research, development, and testing\n3. Budget concerns noted for Q3\n\nThe action items you've marked with #task are:\n- Schedule kickoff meeting with stakeholders\n- Finalize resource allocation by end of month\n- Review vendor proposals",
        }
    ]
}


@pytest.fixture
def mock_file_reads():
    """Mock file reads to return our test content."""

    def mock_read_file(file_path):
        if "lilly_persona.md" in file_path:
            return SAMPLE_PERSONA
        elif "workflow_examples.md" in file_path:
            return SAMPLE_WORKFLOWS
        else:
            return ""

    # Create a more flexible mock for open that handles different file paths
    m = mock_open()
    handle = m()
    handle.read.side_effect = mock_read_file

    with patch("builtins.open", m):
        yield m


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run to return a predictable Claude response."""
    with patch("subprocess.run") as mock_run:
        # Configure the mock to return our sample JSON response
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = json.dumps(MOCK_CLAUDE_RESPONSE)
        mock_run.return_value = process_mock
        yield mock_run


@pytest.fixture
def mock_os_path_exists():
    """Mock os.path.exists to return True for our config files."""

    def mock_exists(path):
        if "lilly_persona.md" in path or "workflow_examples.md" in path:
            return True
        return os.path.exists(path)

    with patch("os.path.exists", side_effect=mock_exists):
        yield


@pytest.fixture
def claude_vision_adapter(mock_file_reads, mock_subprocess_run, mock_os_path_exists):
    """Create a ClaudeVisionAdapter with mocked components."""
    config = get_config()
    config.CLAUDE_COMMAND = "claude"
    config.CLAUDE_MODEL = "claude-3-opus-20240229"
    return ClaudeVisionAdapter(config)


@pytest.fixture
def handwriting_adapter(claude_vision_adapter):
    """Create a HandwritingAdapter with mocked components."""
    config = get_config()

    # Create the adapter with our mocked Claude Vision adapter
    adapter = HandwritingAdapter(
        config=config,
        handwriting_web_adapter=None,
        claude_vision_adapter=claude_vision_adapter,
    )

    # Mock the render_rm_file method to return a predictable path
    with patch.object(
        adapter, "render_rm_file", return_value="/tmp/rendered_image.png"
    ):
        yield adapter


@pytest.fixture
def recognition_service(handwriting_adapter):
    """Create a HandwritingRecognitionService with mocked components."""
    config = get_config()
    return HandwritingRecognitionService(
        config=config, handwriting_adapter=handwriting_adapter
    )


def test_claude_includes_persona_in_prompt(claude_vision_adapter, mock_subprocess_run):
    """Test that the Claude adapter includes the persona in the prompt."""
    # Act
    claude_vision_adapter.process_image("/tmp/test_image.png")

    # Assert
    # Verify claude was called with our image
    mock_subprocess_run.assert_called_once()

    # Get the command that was executed
    args = mock_subprocess_run.call_args[0][0]

    # Verify command includes claude and our image path
    assert "claude" in args
    assert "/tmp/test_image.png" in args


def test_handwriting_recognition_flow(recognition_service, mock_subprocess_run):
    """Test the full handwriting recognition flow with Claude Vision."""
    # Act
    result = recognition_service.recognize_from_ink("/tmp/test.rm")

    # Assert
    assert "project timeline" in result
    assert "Project kickoff scheduled for June 15th" in result
    assert "action items you've marked with #task" in result

    # Verify subprocess was called to invoke Claude CLI
    mock_subprocess_run.assert_called_once()


def test_multi_page_recognition_flow(recognition_service, mock_subprocess_run):
    """Test the multi-page recognition flow with Claude Vision."""
    # Arrange
    file_paths = ["/tmp/page1.rm", "/tmp/page2.rm"]

    # Act
    result = recognition_service.recognize_multi_page_ink(file_paths)

    # Assert
    assert "project timeline" in result
    assert "Project kickoff scheduled for June 15th" in result

    # Verify subprocess was called to invoke Claude CLI with multiple images
    mock_subprocess_run.assert_called_once()


def test_persona_loading(claude_vision_adapter, mock_file_reads):
    """Test that the persona content is loaded correctly."""
    # Act
    persona = claude_vision_adapter._get_persona_content()

    # Assert
    assert "Lilly: reMarkable Companion" in persona
    assert "Core Responsibilities" in persona
    assert "Voice and Tone" in persona


def test_workflow_examples_loading(claude_vision_adapter, mock_file_reads):
    """Test that the workflow examples are loaded correctly."""
    # Act
    workflows = claude_vision_adapter._get_workflow_examples()

    # Assert
    assert "Example Workflows" in workflows
    assert "#summarize Tag" in workflows
    assert "#task Tag" in workflows
