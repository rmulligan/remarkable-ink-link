"""Test GitHub models integration with AI adapter."""

import os
from unittest.mock import MagicMock, patch

import pytest

from inklink.adapters.ai_adapter import AIAdapter


class TestGitHubModelsIntegration:
    """Test cases for GitHub models integration."""

    @pytest.fixture
    def mock_env(self):
        """Mock environment variables."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "test_claude_key",
                "GITHUB_TOKEN": "test_github_token",
            },
        ):
            yield

    @pytest.fixture
    def ai_adapter_with_validation(self, mock_env):
        """Create AI adapter with GitHub validation."""
        return AIAdapter(provider="anthropic", validation_provider="github")

    @staticmethod
    def test_github_validation_initialization(ai_adapter_with_validation):
        """Test that GitHub validation is properly initialized."""
        adapter = ai_adapter_with_validation

        assert adapter.provider == "anthropic"
        assert adapter.validation_provider == "github"
        assert adapter.validation_api_key == "test_github_token"
        assert (
            adapter._get_validation_api_base() == "https://models.github.ai/inference"
        )
        assert adapter._get_validation_model() == "openai/gpt-4.1"

    @patch("requests.post")
    def test_validation_flow(self, mock_post, ai_adapter_with_validation):
        """Test the complete validation flow."""
        # Mock primary response (Claude)
        primary_response = MagicMock()
        primary_response.status_code = 200
        primary_response.json.return_value = {
            "content": [{"text": "This is a test response from Claude"}]
        }

        # Mock validation response (GitHub)
        validation_response = MagicMock()
        validation_response.status_code = 200
        validation_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Validation: The response is accurate and complete."
                    }
                }
            ]
        }

        # Configure mock to return different responses for different calls
        mock_post.side_effect = [primary_response, validation_response]

        # Test generation with validation
        success, result = ai_adapter_with_validation.generate_completion(
            prompt="Test prompt", system_prompt="Be helpful"
        )

        # Should be successful
        assert success

        # Should contain both responses
        assert "This is a test response from Claude" in result
        assert "Validation Check (GitHub Copilot):" in result
        assert "Validation: The response is accurate and complete." in result

        # Should have made two API calls
        assert mock_post.call_count == 2

    @staticmethod
    def test_validation_prompt_creation(ai_adapter_with_validation):
        """Test the validation prompt creation."""
        original_prompt = "Explain Python decorators"
        response = "Decorators are functions that modify other functions..."

        validation_prompt = ai_adapter_with_validation._create_validation_prompt(
            original_prompt, response
        )

        assert "Explain Python decorators" in validation_prompt
        assert (
            "Decorators are functions that modify other functions..."
            in validation_prompt
        )
        assert "evaluate" in validation_prompt.lower()
        assert "accuracy" in validation_prompt.lower()

    @staticmethod
    def test_response_combination(ai_adapter_with_validation):
        """Test how responses are combined."""
        primary = "Primary response from Claude"
        validation = "Validation insights from GitHub"

        combined = ai_adapter_with_validation._combine_responses(primary, validation)

        assert primary in combined
        assert "Validation Check (GitHub Copilot):" in combined
        assert validation in combined

    @patch("requests.post")
    def test_validation_failure_graceful_degradation(
        self, mock_post, ai_adapter_with_validation
    ):
        """Test that primary response is returned even if validation fails."""
        # Mock successful primary response
        primary_response = MagicMock()
        primary_response.status_code = 200
        primary_response.json.return_value = {
            "content": [{"text": "Primary response works"}]
        }

        # Mock failed validation response
        validation_response = MagicMock()
        validation_response.status_code = 401
        validation_response.raise_for_status.side_effect = Exception("Unauthorized")

        mock_post.side_effect = [primary_response, validation_response]

        # Should still succeed with primary response
        success, result = ai_adapter_with_validation.generate_completion("Test")

        assert success
        assert "Primary response works" in result
        # Should not contain validation section
        assert "Validation Check" not in result

    @staticmethod
    def test_github_model_selection():
        """Test GitHub model selection and configuration."""
        # Test with custom model
        with patch.dict(os.environ, {"GITHUB_MODEL": "openai/gpt-4"}):
            adapter = AIAdapter(provider="github")
            assert adapter.model == "openai/gpt-4"

        # Test with default model
        adapter = AIAdapter(provider="github")
        assert adapter.model == "openai/gpt-4.1"

    @staticmethod
    def test_github_api_compatibility():
        """Test that GitHub uses OpenAI-compatible API format."""
        adapter = AIAdapter(provider="github")

        # Should use the same completion method as OpenAI
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Test response"}}]
            }
            mock_post.return_value = mock_response

            success, result = adapter.generate_completion("Test")

            # Verify API call format
            call_args = mock_post.call_args
            assert (
                call_args[0][0] == "https://models.github.ai/inference/chat/completions"
            )
            assert "Authorization" in call_args[1]["headers"]
            assert call_args[1]["json"]["model"] == "openai/gpt-4.1"

    @staticmethod
    def test_environment_variable_priority():
        """Test environment variable priority for GitHub token."""
        # Test GITHUB_TOKEN has priority
        with patch.dict(
            os.environ,
            {"GITHUB_TOKEN": "github_pat_token", "GITHUB_API_KEY": "github_api_key"},
        ):
            adapter = AIAdapter(provider="github", validation_provider="github")
            assert adapter.validation_api_key == "github_pat_token"

        # Test fallback to GITHUB_API_KEY
        with patch.dict(os.environ, {"GITHUB_API_KEY": "github_api_key"}, clear=True):
            adapter = AIAdapter(validation_provider="github")
            assert adapter.validation_api_key is None  # No GITHUB_TOKEN available
