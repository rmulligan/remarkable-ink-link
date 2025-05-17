# Claude Code Task Routing Documentation

This document describes the intelligent task routing system implemented in Phase 2.2 of the Claude Code integration.

## Overview

The task routing system intelligently directs AI requests to the most appropriate provider (Claude Code or local LLM) based on:
- Task type and complexity
- Content privacy sensitivity
- User preferences
- Provider availability

## Architecture

### Core Components

1. **LLMServiceManager** (`llm_service_manager.py`)
   - Extended service manager with LLM provider management
   - Intelligent routing algorithm
   - Privacy classification
   - Complexity assessment

2. **Routing Configuration**
   - Task-based routing priorities
   - Privacy-based routing overrides
   - User preference settings
   - Fallback mechanisms

### Routing Algorithm

```python
def route_task(self, task_type: str, content: str, **kwargs) -> Dict[str, Any]:
    # 1. Classify content privacy
    privacy_level = self._classify_content_privacy(content)
    
    # 2. Assess task complexity
    complexity = self._assess_task_complexity(task_type, content)
    
    # 3. Get routing configuration
    task_routing = self.llm_interface.config.get("task_routing", {})
    privacy_routing = self.llm_interface.config.get("privacy_routing", {})
    
    # 4. Apply privacy overrides
    if privacy_level in privacy_routing:
        preferred_providers = privacy_routing[privacy_level]
    else:
        preferred_providers = task_routing.get(task_type, ["local_llm", "claude_code"])
    
    # 5. Adjust based on complexity and preferences
    # 6. Select available provider
    # 7. Return routing decision with explanation
```

## Task Types and Routing

### Code-Related Tasks
Prioritize Claude Code for superior capabilities:
- `code_generation`: Claude Code → Local LLM
- `code_review`: Claude Code → Local LLM
- `debugging`: Claude Code → Local LLM
- `best_practices`: Claude Code → Local LLM
- `technical_summary`: Claude Code → Local LLM

### Structured Text Tasks
Prioritize local models for performance:
- `summary`: Local LLM → Claude Code
- `extraction`: Local LLM → Claude Code
- `formatting`: Local LLM → Claude Code

### General Tasks
Prioritize local models for privacy:
- `general`: Local LLM → Claude Code
- `chat`: Local LLM → Claude Code

### Research & Analysis
Prioritize Claude Code for capabilities:
- `research`: Claude Code → Local LLM
- `analysis`: Claude Code → Local LLM
- `architecture`: Claude Code → Local LLM

## Privacy Classification

Content is classified into three privacy levels:

1. **Private** (restricted to local models only)
   - Keywords: password, secret, confidential, personal, SSN, credit card, API key, token
   - Route: Local LLM only

2. **Corporate** (prefer local, allow cloud with caution)
   - Keywords: proprietary, internal, company, corporate, business, client, customer
   - Route: Local LLM → Claude Code

3. **Public** (prefer cloud capabilities)
   - Default classification
   - Route: Claude Code → Local LLM

## Complexity Assessment

Tasks are assessed on a 0-1 complexity scale:

### Base Complexity Scores
- `debugging`: 0.9 (highest)
- `architecture`: 0.9
- `code_generation`: 0.8
- `research`: 0.8
- `code_review`: 0.7
- `analysis`: 0.7
- `best_practices`: 0.6
- `general`: 0.5
- `summary`: 0.3
- `chat`: 0.3
- `extraction`: 0.2
- `formatting`: 0.1 (lowest)

### Complexity Modifiers
- Content length > 5000 chars: +0.1
- Content length > 10000 chars: +0.2
- Code presence (```, def, class): +0.1

## User Preferences

Configurable via environment variables:

1. **AI_PREFER_CLOUD** (default: true)
   - Prefer cloud providers when complexity > threshold

2. **AI_FALLBACK_ENABLED** (default: true)
   - Allow fallback to any available provider

3. **AI_COMPLEXITY_THRESHOLD** (default: 0.7)
   - Complexity threshold for cloud preference

4. **AI_AUTO_CLASSIFY** (default: true)
   - Automatically classify content privacy

5. **AI_ROUTING_PRIVACY_MODE** (default: "balanced")
   - Overall privacy stance: strict, balanced, relaxed

6. **AI_ROUTING_CLOUD_ENABLED** (default: true)
   - Enable/disable cloud providers globally

## Routing Decision Transparency

Each routing decision includes:

1. **Selected Provider**
   - Which provider was chosen

2. **Privacy Level**
   - Detected privacy classification

3. **Complexity Score**
   - Calculated task complexity

4. **Routing Path**
   - Ordered list of preferred providers

5. **Reasoning**
   - Human-readable explanation of the decision

## Example Usage

```python
# Initialize service manager
service_manager = LLMServiceManager(config=CONFIG)

# Route a code generation task
routing = service_manager.route_task(
    task_type="code_generation",
    content="Create a Python function to calculate factorial"
)

# Result:
{
    "provider": "claude_code",
    "privacy_level": "public",
    "complexity": 0.8,
    "routing_path": ["claude_code", "local_llm"],
    "reasoning": "Routed code_generation task to claude_code. High complexity (0.80) task prioritizes capable cloud providers."
}
```

## Configuration Best Practices

### For Maximum Privacy
```bash
export AI_ROUTING_PRIVACY_MODE="strict"
export AI_ROUTING_CLOUD_ENABLED="false"
export AI_AUTO_CLASSIFY="true"
export AI_PREFER_CLOUD="false"
```

### For Maximum Performance
```bash
export AI_ROUTING_PRIVACY_MODE="relaxed"
export AI_ROUTING_CLOUD_ENABLED="true"
export AI_PREFER_CLOUD="true"
export AI_COMPLEXITY_THRESHOLD="0.5"
```

### For Balanced Approach (Default)
```bash
export AI_ROUTING_PRIVACY_MODE="balanced"
export AI_ROUTING_CLOUD_ENABLED="true"
export AI_PREFER_CLOUD="true"
export AI_COMPLEXITY_THRESHOLD="0.7"
export AI_AUTO_CLASSIFY="true"
export AI_FALLBACK_ENABLED="true"
```

## Future Enhancements

1. **Machine Learning Classification**
   - Replace keyword-based privacy classification with ML model
   - Learn from user privacy preferences over time

2. **Dynamic Complexity Assessment**
   - Analyze code structure, not just presence
   - Consider domain-specific complexity factors

3. **Provider Performance Tracking**
   - Monitor latency and success rates
   - Adjust routing based on historical performance

4. **Cost Optimization**
   - Consider API costs in routing decisions
   - Balance performance with budget constraints

5. **Custom Routing Rules**
   - User-defined routing rules
   - Project-specific routing configurations