# Claude Code Integration Guide

This guide explains how to use the Claude Code integration in InkLink for AI-assisted coding workflows.

## Overview

The Claude Code integration adds powerful cloud-based coding assistance to InkLink, enabling:
- Code generation from handwritten pseudocode
- AI-powered code reviews
- Smart debugging assistance
- Technical documentation generation
- Best practices guidance

## Architecture

### Components

1. **Claude Code Adapter** (`adapters/claude_code_adapter.py`)
   - Interfaces with Claude CLI
   - Handles code generation, review, and debugging
   - Manages sessions and caching

2. **Claude Code Provider** (`providers/claude_code_provider.py`)
   - Implements the unified LLM interface
   - Wraps adapter functionality

3. **Unified LLM Interface** (`services/llm_interface.py`)
   - Provides intelligent task routing
   - Manages privacy settings
   - Handles fallback to local models

4. **Cloud Coder Agent** (`agents/core/cloud_coder_agent.py`)
   - MCP-enabled agent for coding tasks
   - Integrates with reMarkable for output
   - Manages knowledge graph storage

## Setup

### Prerequisites

1. Install Claude CLI:
   ```bash
   # Follow Anthropic's installation guide
   # https://docs.anthropic.com/claude/docs
   ```

2. Configure Claude CLI:
   ```bash
   claude configure
   # Enter your API key when prompted
   ```

### Environment Variables

Add these to your `.env` file:

```bash
# Claude Code Configuration
CLAUDE_CODE_COMMAND=claude
CLAUDE_CODE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_CODE_TIMEOUT=120
CLAUDE_CODE_MAX_TOKENS=8000
CLAUDE_CODE_TEMPERATURE=0.7
CLAUDE_CODE_CACHE_DIR=/tmp/inklink/claude_code_cache

# AI Routing Configuration
AI_ROUTING_CODE_THRESHOLD=0.8
AI_ROUTING_PRIVACY_MODE=balanced
AI_ROUTING_CLOUD_ENABLED=true
```

## Usage

### Basic Usage

```python
from inklink.services.llm_service_manager import LLMServiceManager

# Initialize service manager
service_manager = LLMServiceManager()
llm_interface = service_manager.get_llm_interface()

# Generate code
success, code = llm_interface.generate_code(
    prompt="Create a Python function to sort a list",
    language="python"
)

# Review code
success, feedback = llm_interface.review_code(
    code=your_code,
    language="python",
    instruction="Check for bugs and suggest improvements"
)

# Debug code
success, debug_info = llm_interface.debug_code(
    code=buggy_code,
    error_message="NameError: name 'x' is not defined"
)
```

### Using the Cloud Coder Agent

```python
from inklink.agents.core.cloud_coder_agent import CloudCoderAgent
from inklink.agents.base.agent import AgentConfig

# Configure the agent
config = AgentConfig(
    name="cloud_coder",
    description="Cloud-based coding assistant",
    version="1.0.0",
    capabilities=["code_generation", "code_review", "debugging"],
    mcp_enabled=True
)

# Initialize agent
cloud_coder = CloudCoderAgent(
    config=config,
    claude_code_provider=claude_provider,
    llm_interface=llm_interface,
    remarkable_service=remarkable_service,
    document_service=document_service
)

# Start the agent
await cloud_coder.start()

# Send a request
response = await cloud_coder.handle_request({
    "type": "generate_code",
    "prompt": "Create an async web server",
    "language": "python",
    "upload_to_remarkable": True
})
```

### Session Management

For multi-turn conversations:

```python
# Create a session
session_id = "my_coding_session"
claude_provider.create_session(session_id)

# Generate code with context
success, code = llm_interface.generate_code(
    prompt="Add error handling to the previous function",
    session_id=session_id
)

# Continue the conversation
success, improved = llm_interface.generate_code(
    prompt="Now make it async",
    session_id=session_id
)

# End the session
claude_provider.end_session(session_id)
```

## Privacy and Security

### Privacy Modes

1. **Strict**: Only local models, no cloud usage
2. **Balanced**: Cloud for non-sensitive content (default)
3. **Relaxed**: Prefer cloud for better results

```python
# Set privacy mode
service_manager.update_llm_privacy_settings(
    privacy_mode="strict",
    cloud_enabled=False
)
```

### Content Sensitivity

Mark sensitive content to ensure local processing:

```python
success, code = llm_interface.generate_code(
    prompt="Generate authentication code",
    content_sensitivity="high"  # Forces local processing
)
```

## Workflow Integration

### Ink-to-Code Workflow

1. Write pseudocode on reMarkable with `#code` tag
2. InkLink detects the tag and captures handwriting
3. Claude Vision transcribes the pseudocode
4. Claude Code generates actual code
5. Result uploaded back to reMarkable

### Code Review Workflow

1. Tag code on reMarkable with `#review`
2. InkLink extracts and sends to Claude Code
3. Claude provides review feedback
4. Annotated result saved to reMarkable

### Debug Workflow

1. Write error message and code snippet
2. Tag with `#debug` on reMarkable
3. Claude analyzes and suggests fixes
4. Fixed code returned to reMarkable

## Best Practices

### Prompt Engineering

For better results:

```python
# Be specific about requirements
prompt = """
Create a Python class for a REST API client that:
- Uses async/await
- Handles rate limiting
- Includes retry logic
- Has proper error handling
"""

# Provide context
context = "This is part of a financial data aggregation system"

success, code = llm_interface.generate_code(
    prompt=prompt,
    context=context,
    language="python"
)
```

### Caching

Results are automatically cached:

```python
# Check cache first
cached = claude_provider.get_cached_result(
    operation="code_generation",
    key=prompt,
    max_age=3600  # 1 hour
)

if not cached:
    success, code = llm_interface.generate_code(prompt=prompt)
```

### Error Handling

Always check for errors:

```python
success, result = llm_interface.generate_code(prompt=prompt)

if not success:
    print(f"Error: {result}")
    # Fall back to local model or handle gracefully
else:
    # Use the generated code
    print(result)
```

## Advanced Features

### Knowledge Graph Integration

The Cloud Coder agent stores activities in the knowledge graph:

```python
# Activities are automatically tracked
response = await cloud_coder.handle_request({
    "type": "generate_code",
    "prompt": "Create a data pipeline"
})

# Query later from knowledge graph
coding_activities = knowledge_graph.query(
    entity_type="CodingActivity",
    date_range=("2024-01-01", "2024-12-31")
)
```

### Parallel Processing

Process multiple requests efficiently:

```python
import asyncio

async def process_multiple():
    tasks = [
        llm_interface.generate_code(prompt1),
        llm_interface.review_code(code2),
        llm_interface.debug_code(code3, error3)
    ]
    
    results = await asyncio.gather(*tasks)
    return results
```

### Custom Prompts

Create optimized prompts:

```python
prompt = claude_adapter.create_coding_prompt(
    task_type="refactor",
    details={
        "quality": "performance",
        "constraints": "maintain backward compatibility"
    },
    style_guide="PEP 8"
)
```

## Troubleshooting

### Common Issues

1. **Claude CLI not found**
   ```bash
   export CLAUDE_CODE_COMMAND=/path/to/claude
   ```

2. **API rate limits**
   - Implement backoff and retry
   - Use caching effectively
   - Consider local fallback

3. **Context too long**
   - Split into smaller requests
   - Use session management
   - Summarize previous context

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("inklink.adapters.claude_code_adapter").setLevel(logging.DEBUG)
```

## Examples

See the complete example in `examples/claude_code_demo.py`:

```bash
cd examples
poetry run python claude_code_demo.py
```

## Future Enhancements

- Automatic code testing integration
- Git commit message generation
- PR description automation
- Code explanation animations
- Live coding sessions with reMarkable