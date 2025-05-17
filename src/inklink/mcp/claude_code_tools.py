#!/usr/bin/env python
"""
MCP tools for Claude Code integration.

This module provides MCP-compatible tools for utilizing Claude Code capabilities
within the InkLink ecosystem, enabling code generation, review, debugging,
and technical documentation workflows.
"""

import logging
from typing import Any, Dict

from inklink.adapters.claude_code_adapter import ClaudeCodeAdapter
from inklink.services.llm_service_manager import LLMServiceManager
from inklink.config import CONFIG

logger = logging.getLogger(__name__)


def claude_code_generate(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate code using Claude Code.

    MCP tool for code generation from natural language descriptions,
    pseudocode, or requirements.

    Args:
        params: Dictionary with:
            - prompt: Code generation prompt
            - language: Target programming language (optional)
            - context: Additional context or constraints (optional)
            - session_id: Session ID for multi-turn conversations (optional)

    Returns:
        Dictionary with:
            - success: Whether generation succeeded
            - code: Generated code
            - explanation: Explanation of the code (optional)
            - language: Detected/used programming language
            - session_id: Session ID for follow-up queries
            - provider: Which LLM provider was used
            - error: Error message if failed
    """
    try:
        prompt = params.get("prompt")
        if not prompt:
            return {"success": False, "error": "No prompt provided"}

        language = params.get("language", "")
        context = params.get("context", "")
        session_id = params.get("session_id")

        # Initialize service manager and get routing decision
        service_manager = LLMServiceManager(config=CONFIG)
        routing = service_manager.route_task("code_generation", prompt)

        if not routing.get("provider"):
            return {
                "success": False,
                "error": "No available provider for code generation",
                "routing": routing,
            }

        # Get the selected provider
        provider_name = routing["provider"]
        llm_interface = service_manager.get_llm_interface()

        # Prepare the generation request
        generation_params = {
            "prompt": prompt,
            "task_type": "code_generation",
            "context": context,
            "metadata": {
                "language": language,
                "session_id": session_id,
            },
        }

        # Route through unified interface
        result = llm_interface.route_request(generation_params)

        return {
            "success": result.get("success", False),
            "code": result.get("result", ""),
            "explanation": result.get("explanation"),
            "language": result.get("language", language),
            "session_id": result.get("session_id", session_id),
            "provider": provider_name,
            "routing": routing,
            "error": result.get("error"),
        }

    except Exception as e:
        logger.error(f"Error in claude_code_generate: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def claude_code_review(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Review code using Claude Code.

    MCP tool for code review, identifying issues, suggesting improvements,
    and ensuring best practices.

    Args:
        params: Dictionary with:
            - code: Code to review
            - language: Programming language (optional)
            - focus_areas: Specific areas to focus on (optional)
            - standards: Coding standards to check against (optional)

    Returns:
        Dictionary with:
            - success: Whether review succeeded
            - review: Review feedback and suggestions
            - issues: List of identified issues
            - improvements: Suggested improvements
            - provider: Which LLM provider was used
            - error: Error message if failed
    """
    try:
        code = params.get("code")
        if not code:
            return {"success": False, "error": "No code provided"}

        language = params.get("language", "")
        focus_areas = params.get("focus_areas", [])
        standards = params.get("standards", "")

        # Initialize service manager and get routing decision
        service_manager = LLMServiceManager(config=CONFIG)
        routing = service_manager.route_task("code_review", code)

        if not routing.get("provider"):
            return {
                "success": False,
                "error": "No available provider for code review",
                "routing": routing,
            }

        # Get the selected provider
        provider_name = routing["provider"]
        llm_interface = service_manager.get_llm_interface()

        # Prepare the review request
        review_params = {
            "prompt": code,
            "task_type": "code_review",
            "metadata": {
                "language": language,
                "focus_areas": focus_areas,
                "standards": standards,
            },
        }

        # Route through unified interface
        result = llm_interface.route_request(review_params)

        return {
            "success": result.get("success", False),
            "review": result.get("result", ""),
            "issues": result.get("issues", []),
            "improvements": result.get("improvements", []),
            "provider": provider_name,
            "routing": routing,
            "error": result.get("error"),
        }

    except Exception as e:
        logger.error(f"Error in claude_code_review: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def claude_code_debug(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Debug code using Claude Code.

    MCP tool for debugging code, identifying errors, and suggesting fixes.

    Args:
        params: Dictionary with:
            - code: Code with issues
            - error_message: Error message or stack trace (optional)
            - expected_behavior: What the code should do (optional)
            - actual_behavior: What the code actually does (optional)
            - language: Programming language (optional)

    Returns:
        Dictionary with:
            - success: Whether debugging succeeded
            - analysis: Debug analysis and findings
            - fixes: Suggested fixes
            - explanation: Explanation of the issue
            - fixed_code: Corrected code (optional)
            - provider: Which LLM provider was used
            - error: Error message if failed
    """
    try:
        code = params.get("code")
        if not code:
            return {"success": False, "error": "No code provided"}

        error_message = params.get("error_message", "")
        expected_behavior = params.get("expected_behavior", "")
        actual_behavior = params.get("actual_behavior", "")
        language = params.get("language", "")

        # Initialize service manager and get routing decision
        service_manager = LLMServiceManager(config=CONFIG)
        routing = service_manager.route_task("debugging", code)

        if not routing.get("provider"):
            return {
                "success": False,
                "error": "No available provider for debugging",
                "routing": routing,
            }

        # Get the selected provider
        provider_name = routing["provider"]
        llm_interface = service_manager.get_llm_interface()

        # Prepare the debug request
        debug_params = {
            "prompt": code,
            "task_type": "debugging",
            "context": f"Error: {error_message}\nExpected: {expected_behavior}\nActual: {actual_behavior}",
            "metadata": {
                "language": language,
                "error_message": error_message,
            },
        }

        # Route through unified interface
        result = llm_interface.route_request(debug_params)

        return {
            "success": result.get("success", False),
            "analysis": result.get("result", ""),
            "fixes": result.get("fixes", []),
            "explanation": result.get("explanation"),
            "fixed_code": result.get("fixed_code"),
            "provider": provider_name,
            "routing": routing,
            "error": result.get("error"),
        }

    except Exception as e:
        logger.error(f"Error in claude_code_debug: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def claude_code_best_practices(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get best practices recommendations using Claude Code.

    MCP tool for getting programming best practices, patterns, and
    architectural guidance.

    Args:
        params: Dictionary with:
            - topic: Topic to get best practices for
            - language: Programming language (optional)
            - context: Specific context or use case (optional)
            - level: Experience level (beginner/intermediate/advanced) (optional)

    Returns:
        Dictionary with:
            - success: Whether request succeeded
            - best_practices: Best practices recommendations
            - examples: Code examples demonstrating best practices
            - resources: Additional resources and references
            - provider: Which LLM provider was used
            - error: Error message if failed
    """
    try:
        topic = params.get("topic")
        if not topic:
            return {"success": False, "error": "No topic provided"}

        language = params.get("language", "")
        context = params.get("context", "")
        level = params.get("level", "intermediate")

        # Initialize service manager and get routing decision
        service_manager = LLMServiceManager(config=CONFIG)
        routing = service_manager.route_task("best_practices", topic)

        if not routing.get("provider"):
            return {
                "success": False,
                "error": "No available provider for best practices",
                "routing": routing,
            }

        # Get the selected provider
        provider_name = routing["provider"]
        llm_interface = service_manager.get_llm_interface()

        # Prepare the best practices request
        practices_params = {
            "prompt": topic,
            "task_type": "best_practices",
            "context": context,
            "metadata": {
                "language": language,
                "level": level,
            },
        }

        # Route through unified interface
        result = llm_interface.route_request(practices_params)

        return {
            "success": result.get("success", False),
            "best_practices": result.get("result", ""),
            "examples": result.get("examples", []),
            "resources": result.get("resources", []),
            "provider": provider_name,
            "routing": routing,
            "error": result.get("error"),
        }

    except Exception as e:
        logger.error(f"Error in claude_code_best_practices: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def claude_code_summarize(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Summarize technical documentation or code using Claude Code.

    MCP tool for creating technical summaries of code, documentation,
    research papers, or complex technical content.

    Args:
        params: Dictionary with:
            - content: Content to summarize
            - type: Type of content (code/docs/paper/article) (optional)
            - style: Summary style (brief/detailed/executive) (optional)
            - focus: Specific aspects to focus on (optional)

    Returns:
        Dictionary with:
            - success: Whether summarization succeeded
            - summary: Generated summary
            - key_points: List of key points
            - technical_details: Important technical details
            - provider: Which LLM provider was used
            - error: Error message if failed
    """
    try:
        content = params.get("content")
        if not content:
            return {"success": False, "error": "No content provided"}

        content_type = params.get("type", "general")
        style = params.get("style", "detailed")
        focus = params.get("focus", [])

        # Initialize service manager and get routing decision
        service_manager = LLMServiceManager(config=CONFIG)
        routing = service_manager.route_task("technical_summary", content)

        if not routing.get("provider"):
            return {
                "success": False,
                "error": "No available provider for summarization",
                "routing": routing,
            }

        # Get the selected provider
        provider_name = routing["provider"]
        llm_interface = service_manager.get_llm_interface()

        # Prepare the summarization request
        summary_params = {
            "prompt": content,
            "task_type": "summarization",
            "metadata": {
                "content_type": content_type,
                "style": style,
                "focus": focus,
            },
        }

        # Route through unified interface
        result = llm_interface.route_request(summary_params)

        return {
            "success": result.get("success", False),
            "summary": result.get("result", ""),
            "key_points": result.get("key_points", []),
            "technical_details": result.get("technical_details", {}),
            "provider": provider_name,
            "routing": routing,
            "error": result.get("error"),
        }

    except Exception as e:
        logger.error(f"Error in claude_code_summarize: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def claude_code_manage_session(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Manage Claude Code session for multi-turn conversations.

    MCP tool for managing conversation sessions with Claude Code,
    enabling context preservation across multiple interactions.

    Args:
        params: Dictionary with:
            - action: Session action (create/resume/clear/status)
            - session_id: Session ID for existing sessions (optional)
            - metadata: Additional session metadata (optional)

    Returns:
        Dictionary with:
            - success: Whether action succeeded
            - session_id: Session ID
            - status: Session status
            - context_size: Size of conversation context
            - metadata: Session metadata
            - error: Error message if failed
    """
    try:
        action = params.get("action", "status")
        session_id = params.get("session_id")
        metadata = params.get("metadata", {})

        # Initialize service manager
        service_manager = LLMServiceManager(config=CONFIG)

        # Get Claude Code provider directly for session management
        claude_provider = service_manager.get_llm_provider("claude_code")

        if not claude_provider:
            return {
                "success": False,
                "error": "Claude Code provider not available",
            }

        # Handle session actions
        if action == "create":
            # Create new session
            session_result = claude_provider.create_session(metadata=metadata)

        elif action == "resume":
            if not session_id:
                return {"success": False, "error": "No session_id provided for resume"}
            session_result = claude_provider.resume_session(session_id)

        elif action == "clear":
            if not session_id:
                return {"success": False, "error": "No session_id provided for clear"}
            session_result = claude_provider.clear_session(session_id)

        elif action == "status":
            if session_id:
                session_result = claude_provider.get_session_status(session_id)
            else:
                session_result = claude_provider.get_all_sessions()

        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
            }

        return {
            "success": True,
            "action": action,
            "session_id": session_result.get("session_id", session_id),
            "status": session_result.get("status"),
            "context_size": session_result.get("context_size"),
            "metadata": session_result.get("metadata", metadata),
        }

    except Exception as e:
        logger.error(f"Error in claude_code_manage_session: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# Register all Claude Code MCP tools
def register_claude_code_tools(registry):
    """
    Register all Claude Code MCP tools with the registry.

    Args:
        registry: MCP registry instance
    """
    registry.register_tool("claude_code_generate", claude_code_generate)
    registry.register_tool("claude_code_review", claude_code_review)
    registry.register_tool("claude_code_debug", claude_code_debug)
    registry.register_tool("claude_code_best_practices", claude_code_best_practices)
    registry.register_tool("claude_code_summarize", claude_code_summarize)
    registry.register_tool("claude_code_manage_session", claude_code_manage_session)

    logger.info("Registered 6 Claude Code MCP tools")
