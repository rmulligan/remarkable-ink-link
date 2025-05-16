"""Tests for the AI Service and AI Adapter."""

from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import patch
from urllib.parse import urlparse

import pytest

from inklink.adapters.ai_adapter import AIAdapter
from inklink.services.ai_service import AIService


class MockAIAdapter:
    """Mock implementation of AIAdapter for testing."""

    def __init__(self, *args, **kwargs):
        """Initialize with test data."""
        self.generate_completion_calls = []
        self.generate_structured_completion_calls = []
        self.process_with_context_calls = []
        self.system_prompt = "You are a helpful assistant."
        self.provider = kwargs.get("provider", "openai")
        self.model = kwargs.get("model", "gpt-3.5-turbo")

        # Configure response behavior
        self.should_fail = False
        self.default_response = "This is a mock AI response."

    def ping(self) -> bool:
        """Mock implementation of ping."""
        return not self.should_fail

    def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[bool, str]:
        """Mock implementation of generate_completion."""
        self.generate_completion_calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }
        )

        if self.should_fail:
            return False, "Mock AI error"

        return True, self.default_response

    def generate_structured_completion(
        self,
        query_text: str,
        context: Optional[Dict[str, Any]] = None,
        structured_content: Optional[
            Union[List[Dict[str, Any]], Dict[str, Any]]
        ] = None,
        context_window: Optional[int] = None,
        selected_pages: Optional[List[Union[int, str]]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> Tuple[bool, str]:
        """Mock implementation of generate_structured_completion."""
        self.generate_structured_completion_calls.append(
            {
                "query_text": query_text,
                "context": context,
                "structured_content": structured_content,
                "context_window": context_window,
                "selected_pages": selected_pages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )

        if self.should_fail:
            return False, "Mock AI structured error"

        # Create a context-aware response if we have context
        if structured_content:
            return (
                True,
                f"Response about {len(self.generate_structured_completion_calls)} documents",
            )
        elif context:
            context_keys = ", ".join(context.keys())
            return True, f"Response with context keys: {context_keys}"

        return True, self.default_response

    def process_with_context(
        self, prompt: str, new_conversation: bool = False, **kwargs
    ) -> Tuple[bool, str, str]:
        """Mock implementation of process_with_context."""
        # Track the call
        self.process_with_context_calls.append(
            {"prompt": prompt, "new_conversation": new_conversation, **kwargs}
        )

        # Simulate the behavior of ClaudeCliAdapter.process_with_context
        # It returns (success, response, conversation_id)
        if self.should_fail:
            return False, "Mock AI error", ""

        response = self.default_response
        conversation_id = "mock_conversation_123"

        return True, response, conversation_id


@pytest.fixture
def mock_adapter():
    """Provide a mock AIAdapter."""
    return MockAIAdapter()


@pytest.fixture
def ai_service(mock_adapter):
    """Create an AIService with a mock adapter."""
    return AIService(adapter=mock_adapter)


def test_ask_success(ai_service, mock_adapter):
    """Test successful simple query."""
    response = ai_service.ask("What is machine learning?")

    # Check response
    assert response == mock_adapter.default_response

    # Verify adapter was called correctly
    assert len(mock_adapter.process_with_context_calls) == 1
    call = mock_adapter.process_with_context_calls[0]
    assert call["prompt"] == "What is machine learning?"
    assert call["new_conversation"] is True


def test_ask_failure(ai_service, mock_adapter):
    """Test handling of failed simple query."""
    mock_adapter.should_fail = True
    response = ai_service.ask("What is machine learning?")

    # Check empty response on failure
    assert response == ""

    # Verify adapter was still called
    assert len(mock_adapter.process_with_context_calls) == 1


def test_process_query_simple(ai_service, mock_adapter):
    """Test processing a simple query without context."""
    response = ai_service.process_query("What is the capital of France?")

    # Check response
    assert response == mock_adapter.default_response

    # Verify adapter was called correctly
    assert len(mock_adapter.generate_structured_completion_calls) == 1
    call = mock_adapter.generate_structured_completion_calls[0]
    assert call["query_text"] == "What is the capital of France?"
    assert call["context"] is None
    assert call["structured_content"] is None


def test_process_query_with_context(ai_service, mock_adapter):
    """Test processing a query with context dictionary."""
    context = {"document_title": "Geography Facts", "author": "John Doe"}
    response = ai_service.process_query(
        "What does this document say about France?", context=context
    )

    # Check context-aware response
    assert "context keys" in response
    assert "document_title" in response
    assert "author" in response

    # Verify adapter was called correctly
    assert len(mock_adapter.generate_structured_completion_calls) == 1
    call = mock_adapter.generate_structured_completion_calls[0]
    assert call["context"] == context


def test_process_query_with_structured_content(ai_service, mock_adapter):
    """Test processing a query with structured document content."""
    structured_content = {
        "pages": [
            {
                "number": 1,
                "title": "Introduction",
                "content": "This is an introduction to geography.",
                "links": [{"target": 2, "label": "Europe"}],
            },
            {
                "number": 2,
                "title": "Europe",
                "content": "Europe is a continent with many countries.",
                "links": [],
            },
        ]
    }

    response = ai_service.process_query(
        "Tell me about Europe", structured_content=structured_content
    )

    # Check structured content response
    assert "Response about" in response
    assert "documents" in response

    # Verify adapter was called correctly
    assert len(mock_adapter.generate_structured_completion_calls) == 1
    call = mock_adapter.generate_structured_completion_calls[0]
    assert call["structured_content"] == structured_content


def test_process_query_with_selection(ai_service, mock_adapter):
    """Test processing a query with page selection."""
    structured_content = {
        "pages": [
            {"number": 1, "title": "Page 1", "content": "Content 1"},
            {"number": 2, "title": "Page 2", "content": "Content 2"},
            {"number": 3, "title": "Page 3", "content": "Content 3"},
        ]
    }

    ai_service.process_query(
        "Show me page 2", structured_content=structured_content, selected_pages=[2]
    )

    # Verify adapter was called correctly
    assert len(mock_adapter.generate_structured_completion_calls) == 1
    call = mock_adapter.generate_structured_completion_calls[0]
    assert call["structured_content"] == structured_content
    assert call["selected_pages"] == [2]


def test_process_query_failure(ai_service, mock_adapter):
    """Test handling of failed structured query."""
    mock_adapter.should_fail = True
    response = ai_service.process_query("What is machine learning?")

    # Check empty response on failure
    assert response == ""

    # Verify adapter was still called
    assert len(mock_adapter.generate_structured_completion_calls) == 1


def test_adapter_initialization():
    """Test that AIAdapter initializes with the right defaults."""
    # Test with OpenAI provider
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
        adapter = AIAdapter()
        assert adapter.provider == "openai"
        assert adapter.api_key == "test_key"
        assert adapter.model == "gpt-3.5-turbo"

        # Parse the API base URL to check domain properly
        parsed_url = urlparse(adapter.api_base)
        assert parsed_url.netloc == "api.openai.com" or parsed_url.netloc.endswith(
            ".api.openai.com"
        )

    # Test with Anthropic provider
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_anthropic_key"}):
        adapter = AIAdapter(provider="anthropic")
        assert adapter.provider == "anthropic"
        assert adapter.api_key == "test_anthropic_key"
        assert "claude" in adapter.model

        # Parse the API base URL to check domain properly
        parsed_url = urlparse(adapter.api_base)
        assert parsed_url.netloc == "api.anthropic.com" or parsed_url.netloc.endswith(
            ".api.anthropic.com"
        )


def test_build_system_prompt_with_context(mock_adapter):
    """Test building system prompt with context."""
    # Create a real adapter to test internal methods
    adapter = AIAdapter(api_key="dummy_key")

    # Test with context dict
    context = {"topic": "Geography", "level": "Beginner"}
    prompt = adapter._build_system_prompt_with_context(context=context)
    assert "Document context:" in prompt
    assert "Geography" in prompt
    assert "Beginner" in prompt

    # Test with structured content
    structured_content = {
        "pages": [
            {
                "title": "Introduction",
                "content": "This is the introduction.",
                "number": 1,
            },
            {"title": "Chapter 1", "content": "This is chapter 1.", "number": 2},
        ]
    }
    prompt = adapter._build_system_prompt_with_context(
        structured_content=structured_content
    )
    assert "Relevant document context:" in prompt
    assert "Introduction" in prompt
    assert "Chapter 1" in prompt

    # Test with page selection
    prompt = adapter._build_system_prompt_with_context(
        structured_content=structured_content, selected_pages=[2]
    )
    assert "Introduction" not in prompt
    assert "Chapter 1" in prompt

    # Test with context window
    structured_content = {
        "pages": [
            {"title": "Page 1", "content": "Content 1", "number": 1},
            {"title": "Page 2", "content": "Content 2", "number": 2},
            {"title": "Page 3", "content": "Content 3", "number": 3},
        ]
    }
    prompt = adapter._build_system_prompt_with_context(
        structured_content=structured_content, context_window=2
    )
    assert "Page 1" not in prompt
    assert "Page 2" in prompt
    assert "Page 3" in prompt
