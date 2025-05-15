# GitHub Models Integration

This document describes how GitHub Copilot models are integrated into the remarkable-ink-link project to provide enhanced AI capabilities with checks and balances alongside Claude.

## Overview

The integration adds GitHub's AI models as a secondary validation layer to existing AI services, providing:

1. **Cross-validation**: GitHub models validate responses from primary AI providers
2. **Enhanced accuracy**: Ensemble approach combining multiple model outputs
3. **Cost optimization**: Using GitHub models available with Copilot subscriptions
4. **Specialized insights**: GitHub models excel at code understanding and technical content

## Architecture

### AI Adapter Enhancement

The `AIAdapter` class now supports:
- Primary provider (e.g., Claude, OpenAI)
- Optional validation provider (GitHub models)
- Ensemble response combination

```python
# Example configuration
ai_adapter = AIAdapter(
    provider="anthropic",
    model="claude-3-sonnet-20240229",
    validation_provider="github",  # Enables GitHub validation
    api_key=claude_api_key
)
```

### Environment Variables

```bash
# Primary AI configuration
ANTHROPIC_API_KEY=your_claude_key
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# GitHub validation configuration
GITHUB_TOKEN=your_github_pat_token  # Personal Access Token with models:read
GITHUB_MODEL=openai/gpt-4.1  # Optional, defaults to gpt-4.1
```

### Setting Up GitHub Personal Access Token

For GitHub Actions workflow integration with GitHub Models, you need to:

1. Create a Personal Access Token (PAT) - Optional but Recommended:
   - Go to https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select the `models:read` scope
   - Give it a descriptive name like "GitHub Models API Access"
   - Set an expiration that works for your needs

2. Add the PAT to your repository secrets:
   - Go to your repository settings
   - Navigate to Secrets and variables > Actions
   - Create a new repository secret named `PAT_TOKEN`
   - Paste your PAT as the value

3. The workflow will use this secret to authenticate with GitHub Models API:
   ```yaml
   env:
     GITHUB_TOKEN: ${{ secrets.PAT_TOKEN || secrets.GITHUB_TOKEN }}
   ```

**Note**: If no PAT is provided, the workflow will automatically fall back to a basic local analysis using pattern matching and code statistics. This provides a baseline code review even without access to GitHub Models API.

## Use Cases

### 1. Handwriting Recognition Validation

```python
# Primary recognition with Claude Vision
recognition_result = claude_vision.recognize_handwriting(image)

# GitHub validates and enhances the result
if ai_adapter.validation_provider:
    enhanced_result = ai_adapter.generate_completion(
        f"Review this handwriting recognition: {recognition_result}",
        system_prompt="Focus on code syntax and technical accuracy"
    )
```

### 2. Code Understanding Enhancement

GitHub models excel at:
- Detecting code syntax in handwritten notes
- Validating code correctness
- Suggesting improvements and optimizations
- Identifying potential bugs or security issues

### 3. Technical Documentation

The ensemble approach provides:
- Primary response from Claude (natural language understanding)
- Validation from GitHub (technical accuracy)
- Combined result with both perspectives

## Security Considerations

1. **PAT Token Management**:
   - Store GitHub PAT securely as environment variable
   - Grant only required permissions (models:read)
   - Rotate tokens regularly

2. **Data Privacy**:
   - Handwriting data is sent to GitHub's model endpoints
   - Consider data sensitivity when enabling validation
   - Use validation selectively for non-sensitive content

3. **Error Handling**:
   - Primary responses are returned even if validation fails
   - Validation errors are logged but don't block the primary flow
   - Graceful degradation ensures service continuity

## Configuration Examples

### Basic Setup

```python
# For handwriting recognition with validation
ai_service = AIService(
    provider="anthropic",
    validation_provider="github"
)
```

### Advanced Configuration

```python
# Custom validation prompts for specific use cases
class CodeValidationAdapter(AIAdapter):
    def _create_validation_prompt(self, original_prompt: str, response: str) -> str:
        return f"""
        Analyze this code-related response:
        
        Original: {original_prompt}
        Response: {response}
        
        Check for:
        1. Syntax correctness
        2. Best practices
        3. Security concerns
        4. Performance implications
        """
```

## Benefits

1. **Improved Accuracy**: Cross-validation catches errors and improves quality
2. **Cost Effective**: Leverages existing Copilot subscription
3. **Specialized Knowledge**: GitHub models excel at code understanding
4. **Flexibility**: Optional validation can be enabled/disabled per request
5. **Transparency**: Users see both primary and validation responses

## Future Enhancements

1. **Weighted Ensemble**: Combine responses based on confidence scores
2. **Task-Specific Routing**: Use GitHub for code, Claude for natural language
3. **Multi-Model Validation**: Add more providers for consensus
4. **Caching**: Store validation results for similar queries
5. **Metrics**: Track accuracy improvements from validation

## Code Review Workflow

The project includes an automated code review workflow that runs on pull requests:

### How It Works

1. **PR Analysis**: The workflow fetches the PR diff when a new PR is opened or updated
2. **AI Review**: Attempts to use GitHub Models (gpt-4o-mini) for intelligent code review
3. **Fallback**: If GitHub Models is unavailable, performs a basic local analysis
4. **Comments**: Posts the review as a comment on the PR

### Workflow Features

#### With GitHub Models (PAT Required)
- Comprehensive code review using AI
- Identifies potential bugs and issues
- Suggests improvements and best practices
- Provides code quality assessment

#### Fallback Local Analysis (No PAT Required)
- Basic change statistics (lines added/removed)
- Security pattern detection (eval, exec, etc.)
- Test coverage detection
- General recommendations

### Configuration

The workflow is configured in `.github/workflows/code-review-github-models.yml`

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   ```bash
   export GITHUB_TOKEN="ghp_your_token_here"
   ```
   
   For the workflow: If you see "The `models` permission is required", the workflow will automatically fall back to local analysis

2. **Model Access**:
   - Ensure PAT has models:read permission
   - Verify Copilot subscription is active
   - Check repository secrets for `PAT_TOKEN`

3. **Rate Limits**:
   - GitHub models have usage limits
   - Implement exponential backoff
   - Cache validation results when possible

### Debug Mode

Enable debug logging to see validation flow:
```python
import logging
logging.getLogger("inklink.adapters.ai_adapter").setLevel(logging.DEBUG)
```