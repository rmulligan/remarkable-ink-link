# Claude-Only AI Integration

## Summary of Changes

We've updated the InkLink project to use only the Claude CLI as the AI assistant agent, removing all OpenAI-specific functionality. This simplifies the codebase and aligns with the preferred AI provider.

## Changes Made

1. **Created Claude CLI Adapter**
   - Added a new `claude_cli_adapter.py` class specifically designed to interact with Claude through the CLI
   - Implemented Claude-specific methods for generating completions and maintaining conversation context
   - Added support for conversation IDs tracking for persistent context

2. **Updated AI Service**
   - Modified `ai_service.py` to use the Claude CLI adapter exclusively
   - Removed OpenAI provider options and API-specific code
   - Updated method implementations to work with Claude CLI

3. **Configuration Updates**
   - Removed OpenAI-specific settings from `config.py`
   - Added Claude-specific system prompt configuration
   - Simplified AI provider configuration

4. **CLI Command Updates**
   - Updated the `ask` command in `main.py` to specify Claude model instead of OpenAI
   - Maintained the same interface for backward compatibility

## Benefits

1. **Simplified Dependency Model**: Removed the need for OpenAI API keys and authentication
2. **Improved Local Processing**: All AI interactions now happen through the local Claude CLI
3. **Consistent User Experience**: Single AI provider ensures consistent response quality and format
4. **Reduced Complexity**: Removed multi-provider code paths that were unnecessary

## Usage

The AI functionality still works the same way from the user's perspective:

```bash
# Ask a question to Claude and upload response to reMarkable
python -m inklink.main ask --prompt "Your question here"

# Specify a specific Claude model
python -m inklink.main ask --prompt "Your question here" --model "claude-3-opus-20240229"
```

## Note on External References

There are a few mentions of OpenAI in the documentation files (README.md, round_trip_workflow.md, inklink-dev-briefing.md), but these are general references to the project's capabilities rather than specific implementation details. These references were left unchanged as they provide context about the project's architecture and potential integration points.