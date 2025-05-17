# Claude Code MCP Tools and Capabilities

This document describes the Model Context Protocol (MCP) tools and capabilities available for Claude Code integration in InkLink.

## Overview

The Claude Code integration provides several MCP-enabled tools that allow agents to perform code-related tasks. These tools follow the InkLink MCP pattern and are exposed through the Cloud Coder agent.

## MCP Architecture in InkLink

InkLink uses a capability-based MCP system where:

1. Each agent registers MCP capabilities using `MCPCapability` objects
2. Capabilities include:
   - Name: Unique identifier for the capability
   - Description: Human-readable description
   - Handler: Async function to handle requests
   - Input Schema: JSON Schema for validation
   - Output Schema: Expected response format

## Claude Code MCP Capabilities

The Cloud Coder agent provides the following MCP capabilities:

### 1. generate_code

**Purpose**: Generate code from handwritten pseudocode or natural language

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "prompt": {
      "type": "string",
      "description": "Code generation prompt"
    },
    "language": {
      "type": "string",
      "description": "Target programming language"
    },
    "context": {
      "type": "string",
      "description": "Additional context"
    },
    "session_id": {
      "type": "string",
      "description": "Session ID for context"
    },
    "upload_to_remarkable": {
      "type": "boolean",
      "description": "Upload result to reMarkable",
      "default": true
    }
  },
  "required": ["prompt"]
}
```

**Output**: Generated code and optional reMarkable upload status

### 2. review_code

**Purpose**: Review code and provide feedback

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "code": {
      "type": "string",
      "description": "Code to review"
    },
    "language": {
      "type": "string",
      "description": "Programming language"
    },
    "focus": {
      "type": "string",
      "description": "Review focus area"
    },
    "session_id": {
      "type": "string",
      "description": "Session ID for context"
    },
    "upload_to_remarkable": {
      "type": "boolean",
      "description": "Upload review to reMarkable",
      "default": true
    }
  },
  "required": ["code"]
}
```

**Output**: Review feedback with issues, improvements, and best practices

### 3. debug_code

**Purpose**: Debug code and suggest fixes

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "code": {
      "type": "string",
      "description": "Code with errors"
    },
    "error_message": {
      "type": "string",
      "description": "Error message"
    },
    "stack_trace": {
      "type": "string",
      "description": "Stack trace if available"
    },
    "session_id": {
      "type": "string",
      "description": "Session ID for context"
    },
    "upload_to_remarkable": {
      "type": "boolean",
      "description": "Upload debug results to reMarkable",
      "default": true
    }
  },
  "required": ["code", "error_message"]
}
```

**Output**: Debug analysis with error explanation, root cause, and suggested fixes

### 4. ask_best_practices

**Purpose**: Ask for coding best practices and technical guidance

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Technical question"
    },
    "language": {
      "type": "string",
      "description": "Programming language context"
    },
    "context": {
      "type": "string",
      "description": "Additional context"
    },
    "session_id": {
      "type": "string",
      "description": "Session ID for context"
    },
    "upload_to_remarkable": {
      "type": "boolean",
      "description": "Upload response to reMarkable",
      "default": true
    }
  },
  "required": ["query"]
}
```

**Output**: Best practices advice

### 5. summarize_technical

**Purpose**: Summarize technical documentation or code discussions

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "content": {
      "type": "string",
      "description": "Content to summarize"
    },
    "focus": {
      "type": "string",
      "description": "Focus area for summary"
    },
    "max_length": {
      "type": "integer",
      "description": "Maximum summary length"
    },
    "session_id": {
      "type": "string",
      "description": "Session ID for context"
    },
    "upload_to_remarkable": {
      "type": "boolean",
      "description": "Upload summary to reMarkable",
      "default": true
    }
  },
  "required": ["content"]
}
```

**Output**: Technical summary

### 6. manage_session

**Purpose**: Manage coding session for context

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "session_id": {
      "type": "string",
      "description": "Session identifier"
    },
    "action": {
      "type": "string",
      "enum": ["create", "resume", "end", "status"],
      "description": "Session action"
    }
  },
  "required": ["session_id", "action"]
}
```

**Output**: Session status information

### 7. Default Capabilities

The Cloud Coder agent also inherits default MCP capabilities:

- **health_check**: Check agent health status
- **get_status**: Get agent status information

## Integration with Other MCP Tools

Claude Code can work with other InkLink MCP tools:

1. **Knowledge Graph Tools**: Store coding activities and relationships
2. **Augmented Notebook Tools**: Process handwritten code notebooks
3. **Knowledge Index Tools**: Index technical documentation

## Using Claude Code MCP Tools

### From Other Agents

Other agents can use Claude Code capabilities through MCP messaging:

```python
# Example: Another agent using Claude Code
response = await self.send_mcp_message(
    target="cloud_coder",
    capability="generate_code",
    data={
        "prompt": "Create a Python function to sort a list",
        "language": "python"
    }
)
```

### Direct Integration

The Cloud Coder agent can be integrated directly:

```python
from inklink.agents.core.cloud_coder_agent import CloudCoderAgent

# Initialize agent with required services
cloud_coder = CloudCoderAgent(config, providers, services)

# Handle a request
result = await cloud_coder.handle_request({
    "type": "generate_code",
    "prompt": "Create a REST API endpoint",
    "language": "python"
})
```

## Session Management

The Claude Code MCP tools support session management for maintaining context across multiple interactions:

1. Create a session for a coding workflow
2. Use the session ID in subsequent requests
3. End the session when complete

## Knowledge Graph Integration

Coding activities are automatically stored in the knowledge graph:

- Each operation creates a "CodingActivity" entity
- Sessions are linked as relationships
- Code generation metrics are tracked

## Best Practices

1. **Use sessions for multi-turn workflows**: Create a session when starting a complex coding task
2. **Provide language context**: Always specify the programming language for better results
3. **Enable reMarkable upload**: Allow results to be uploaded for handwritten workflows
4. **Handle errors gracefully**: Check for error responses in the output

## Future Enhancements

Potential MCP tools to add:

1. **refactor_code**: Automated code refactoring suggestions
2. **generate_tests**: Unit test generation from code
3. **analyze_performance**: Performance analysis and optimization
4. **convert_language**: Code translation between languages
5. **generate_documentation**: Automatic documentation generation

## Security Considerations

- Session data is cached locally
- Sensitive code can be routed to local models
- Knowledge graph storage respects privacy settings
- MCP communication is internal to the InkLink system