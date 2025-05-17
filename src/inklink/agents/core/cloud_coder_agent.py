#!/usr/bin/env python
"""Cloud Coder Agent for AI-assisted coding via Claude Code."""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from inklink.agents.base.agent import AgentConfig
from inklink.agents.base.mcp_integration import MCPCapability, MCPEnabledAgent
from inklink.providers.claude_code_provider import ClaudeCodeProvider
from inklink.services.document_service import DocumentService
from inklink.services.knowledge_graph_service import KnowledgeGraphService
from inklink.services.llm_interface import UnifiedLLMInterface
from inklink.services.remarkable_service import RemarkableService


class CloudCoderAgent(MCPEnabledAgent):
    """Agent that provides cloud-based coding assistance using Claude Code."""

    def __init__(
        self,
        config: AgentConfig,
        claude_code_provider: ClaudeCodeProvider,
        llm_interface: UnifiedLLMInterface,
        remarkable_service: RemarkableService,
        document_service: DocumentService,
        knowledge_graph_service: Optional[KnowledgeGraphService] = None,
        cache_path: Optional[Path] = None,
    ):
        """
        Initialize the Cloud Coder agent.

        Args:
            config: Agent configuration
            claude_code_provider: Claude Code provider instance
            llm_interface: Unified LLM interface for intelligent routing
            remarkable_service: Service for reMarkable integration
            document_service: Service for document generation
            knowledge_graph_service: Optional knowledge graph integration
            cache_path: Optional path for caching results
        """
        super().__init__(config)
        self.claude_code = claude_code_provider
        self.llm_interface = llm_interface
        self.remarkable_service = remarkable_service
        self.document_service = document_service
        self.knowledge_graph = knowledge_graph_service

        # Cache directory for results
        self.cache_path = cache_path or Path.home() / ".inklink" / "cloud_coder_cache"
        self.cache_path.mkdir(parents=True, exist_ok=True)

        # Session management
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        # Setup MCP capabilities
        self._setup_mcp_capabilities()

        # Stats tracking
        self.stats = {
            "code_generated": 0,
            "reviews_performed": 0,
            "debug_requests": 0,
            "best_practices_queries": 0,
            "summaries_created": 0,
        }

    def _setup_mcp_capabilities(self) -> None:
        """Set up MCP capabilities for cloud coding assistance."""

        # Generate code capability
        self.register_mcp_capability(
            MCPCapability(
                name="generate_code",
                description="Generate code from handwritten pseudocode or natural language",
                handler=self._handle_generate_code,
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Code generation prompt",
                        },
                        "language": {
                            "type": "string",
                            "description": "Target programming language",
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context",
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Session ID for context",
                        },
                        "upload_to_remarkable": {
                            "type": "boolean",
                            "description": "Upload result to reMarkable",
                            "default": True,
                        },
                    },
                    "required": ["prompt"],
                },
            )
        )

        # Review code capability
        self.register_mcp_capability(
            MCPCapability(
                name="review_code",
                description="Review code and provide feedback",
                handler=self._handle_review_code,
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Code to review"},
                        "language": {
                            "type": "string",
                            "description": "Programming language",
                        },
                        "focus": {"type": "string", "description": "Review focus area"},
                        "session_id": {
                            "type": "string",
                            "description": "Session ID for context",
                        },
                        "upload_to_remarkable": {
                            "type": "boolean",
                            "description": "Upload review to reMarkable",
                            "default": True,
                        },
                    },
                    "required": ["code"],
                },
            )
        )

        # Debug code capability
        self.register_mcp_capability(
            MCPCapability(
                name="debug_code",
                description="Debug code and suggest fixes",
                handler=self._handle_debug_code,
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Code with errors"},
                        "error_message": {
                            "type": "string",
                            "description": "Error message",
                        },
                        "stack_trace": {
                            "type": "string",
                            "description": "Stack trace if available",
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Session ID for context",
                        },
                        "upload_to_remarkable": {
                            "type": "boolean",
                            "description": "Upload debug results to reMarkable",
                            "default": True,
                        },
                    },
                    "required": ["code", "error_message"],
                },
            )
        )

        # Best practices capability
        self.register_mcp_capability(
            MCPCapability(
                name="ask_best_practices",
                description="Ask for coding best practices and technical guidance",
                handler=self._handle_best_practices,
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Technical question",
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language context",
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context",
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Session ID for context",
                        },
                        "upload_to_remarkable": {
                            "type": "boolean",
                            "description": "Upload response to reMarkable",
                            "default": True,
                        },
                    },
                    "required": ["query"],
                },
            )
        )

        # Summarize technical content
        self.register_mcp_capability(
            MCPCapability(
                name="summarize_technical",
                description="Summarize technical documentation or code discussions",
                handler=self._handle_summarize,
                input_schema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Content to summarize",
                        },
                        "focus": {
                            "type": "string",
                            "description": "Focus area for summary",
                        },
                        "max_length": {
                            "type": "integer",
                            "description": "Maximum summary length",
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Session ID for context",
                        },
                        "upload_to_remarkable": {
                            "type": "boolean",
                            "description": "Upload summary to reMarkable",
                            "default": True,
                        },
                    },
                    "required": ["content"],
                },
            )
        )

        # Manage sessions
        self.register_mcp_capability(
            MCPCapability(
                name="manage_session",
                description="Manage coding session for context",
                handler=self._handle_manage_session,
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session identifier",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["create", "resume", "end", "status"],
                            "description": "Session action",
                        },
                    },
                    "required": ["session_id", "action"],
                },
            )
        )

    async def _agent_logic(self) -> None:
        """Main agent logic - periodically check for tasks or maintain state."""
        # This agent is primarily reactive to MCP calls
        # Could add proactive features like:
        # - Monitoring for code-related tags in notes
        # - Checking for scheduled code reviews
        # - Background best practice analysis
        await asyncio.sleep(60)  # Check every minute

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        request_type = request.get("type", "")

        if request_type == "generate_code":
            return await self._handle_generate_code(request)
        elif request_type == "review_code":
            return await self._handle_review_code(request)
        elif request_type == "debug_code":
            return await self._handle_debug_code(request)
        elif request_type == "best_practices":
            return await self._handle_best_practices(request)
        elif request_type == "summarize":
            return await self._handle_summarize(request)
        elif request_type == "session":
            return await self._handle_manage_session(request)
        else:
            return {"error": f"Unknown request type: {request_type}"}

    async def _handle_generate_code(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code generation request."""
        try:
            prompt = request["prompt"]
            language = request.get("language")
            context = request.get("context")
            session_id = request.get("session_id")
            upload = request.get("upload_to_remarkable", True)

            # Use privacy-aware routing
            content_sensitivity = request.get("sensitivity", "normal")

            success, code = await self.llm_interface.generate_code(
                prompt=prompt,
                language=language,
                context=context,
                session_id=session_id,
                content_sensitivity=content_sensitivity,
            )

            if not success:
                return {"error": f"Code generation failed: {code}"}

            # Update stats
            self.stats["code_generated"] += 1

            # Create result document
            result = {
                "code": code,
                "language": language or "unknown",
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
            }

            # Upload to reMarkable if requested
            if upload:
                doc_path = await self._create_code_document(
                    code, f"Generated {language or 'code'}", prompt
                )
                if doc_path:
                    success, message = self.remarkable_service.upload(
                        doc_path, f"Code: {language or 'Generated'}"
                    )
                    result["uploaded"] = success
                    result["upload_message"] = message

            # Cache the result
            self._cache_result("code_generation", prompt, result)

            # Store in knowledge graph if available
            if self.knowledge_graph:
                await self._store_in_knowledge_graph("code_generation", prompt, result)

            return result

        except Exception as e:
            self.logger.error(f"Error generating code: {e}")
            return {"error": str(e)}

    async def _handle_review_code(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code review request."""
        try:
            code = request["code"]
            language = request.get("language")
            focus = request.get("focus")
            session_id = request.get("session_id")
            upload = request.get("upload_to_remarkable", True)

            # Determine content sensitivity
            content_sensitivity = request.get("sensitivity", "normal")

            success, feedback = await self.llm_interface.review_code(
                code=code,
                language=language,
                instruction=focus,
                session_id=session_id,
                content_sensitivity=content_sensitivity,
            )

            if not success:
                return {"error": f"Code review failed: {feedback}"}

            # Update stats
            self.stats["reviews_performed"] += 1

            # Create result
            result = {
                "feedback": feedback,
                "language": language or "unknown",
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
            }

            # Upload to reMarkable if requested
            if upload:
                # Format feedback for display
                formatted_feedback = self._format_review_feedback(feedback)
                doc_path = await self._create_review_document(
                    code, formatted_feedback, language
                )
                if doc_path:
                    success, message = self.remarkable_service.upload(
                        doc_path, f"Code Review: {language or 'General'}"
                    )
                    result["uploaded"] = success
                    result["upload_message"] = message

            return result

        except Exception as e:
            self.logger.error(f"Error reviewing code: {e}")
            return {"error": str(e)}

    async def _handle_debug_code(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code debugging request."""
        try:
            code = request["code"]
            error_message = request["error_message"]
            stack_trace = request.get("stack_trace")
            session_id = request.get("session_id")
            upload = request.get("upload_to_remarkable", True)

            success, debug_info = await self.llm_interface.debug_code(
                code=code,
                error_message=error_message,
                stack_trace=stack_trace,
                session_id=session_id,
            )

            if not success:
                return {"error": f"Debugging failed: {debug_info}"}

            # Update stats
            self.stats["debug_requests"] += 1

            # Create result
            result = {
                "debug_info": debug_info,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
            }

            # Upload to reMarkable if requested
            if upload:
                doc_path = await self._create_debug_document(
                    code, error_message, debug_info
                )
                if doc_path:
                    success, message = self.remarkable_service.upload(
                        doc_path, "Debug Analysis"
                    )
                    result["uploaded"] = success
                    result["upload_message"] = message

            return result

        except Exception as e:
            self.logger.error(f"Error debugging code: {e}")
            return {"error": str(e)}

    async def _handle_best_practices(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle best practices query."""
        try:
            query = request["query"]
            language = request.get("language")
            context = request.get("context")
            session_id = request.get("session_id")
            upload = request.get("upload_to_remarkable", True)

            success, advice = await self.llm_interface.ask_best_practices(
                query=query,
                language=language,
                context=context,
                session_id=session_id,
            )

            if not success:
                return {"error": f"Best practices query failed: {advice}"}

            # Update stats
            self.stats["best_practices_queries"] += 1

            # Create result
            result = {
                "advice": advice,
                "language": language,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
            }

            # Upload to reMarkable if requested
            if upload:
                doc_path = await self._create_best_practices_document(
                    query, advice, language
                )
                if doc_path:
                    success, message = self.remarkable_service.upload(
                        doc_path, f"Best Practices: {query[:50]}"
                    )
                    result["uploaded"] = success
                    result["upload_message"] = message

            # Cache the result
            self._cache_result("best_practices", query, result)

            return result

        except Exception as e:
            self.logger.error(f"Error getting best practices: {e}")
            return {"error": str(e)}

    async def _handle_summarize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle technical content summarization."""
        try:
            content = request["content"]
            focus = request.get("focus")
            max_length = request.get("max_length")
            session_id = request.get("session_id")
            upload = request.get("upload_to_remarkable", True)

            # Determine content sensitivity
            content_sensitivity = request.get("sensitivity", "normal")

            success, summary = await self.llm_interface.summarize_text(
                text=content,
                focus=focus,
                max_length=max_length,
                session_id=session_id,
                content_sensitivity=content_sensitivity,
            )

            if not success:
                return {"error": f"Summarization failed: {summary}"}

            # Update stats
            self.stats["summaries_created"] += 1

            # Create result
            result = {
                "summary": summary,
                "focus": focus,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
            }

            # Upload to reMarkable if requested
            if upload:
                doc_path = await self._create_summary_document(summary, focus)
                if doc_path:
                    success, message = self.remarkable_service.upload(
                        doc_path, f"Summary: {focus or 'Technical'}"
                    )
                    result["uploaded"] = success
                    result["upload_message"] = message

            return result

        except Exception as e:
            self.logger.error(f"Error summarizing content: {e}")
            return {"error": str(e)}

    async def _handle_manage_session(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle session management."""
        try:
            session_id = request["session_id"]
            action = request["action"]

            if action == "create":
                success = self.claude_code.create_session(session_id)
                self.active_sessions[session_id] = {
                    "created": datetime.now(),
                    "interactions": 0,
                }
                return {"success": success, "session_id": session_id}

            elif action == "resume":
                if session_id in self.active_sessions:
                    self.active_sessions[session_id]["interactions"] += 1
                    return {"success": True, "session_id": session_id}
                else:
                    return {"error": f"Session {session_id} not found"}

            elif action == "end":
                success = self.claude_code.end_session(session_id)
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]
                return {"success": success}

            elif action == "status":
                if session_id in self.active_sessions:
                    session_info = self.active_sessions[session_id]
                    return {
                        "session_id": session_id,
                        "created": session_info["created"].isoformat(),
                        "interactions": session_info["interactions"],
                    }
                else:
                    return {"error": f"Session {session_id} not found"}

            else:
                return {"error": f"Unknown session action: {action}"}

        except Exception as e:
            self.logger.error(f"Error managing session: {e}")
            return {"error": str(e)}

    async def _create_code_document(
        self, code: str, title: str, prompt: str
    ) -> Optional[str]:
        """Create a document with generated code."""
        try:
            content = {
                "title": title,
                "sections": [
                    {"type": "heading", "content": title},
                    {"type": "text", "content": f"Prompt: {prompt}"},
                    {"type": "code", "content": code},
                    {
                        "type": "text",
                        "content": f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    },
                ],
            }

            return self.document_service.create_rmdoc_from_content(
                url="",  # No URL for generated content
                qr_path=None,
                content=content,
            )
        except Exception as e:
            self.logger.error(f"Error creating code document: {e}")
            return None

    async def _create_review_document(
        self, code: str, feedback: str, language: Optional[str]
    ) -> Optional[str]:
        """Create a document with code review results."""
        try:
            content = {
                "title": f"Code Review: {language or 'General'}",
                "sections": [
                    {"type": "heading", "content": "Code Review"},
                    {"type": "subheading", "content": "Original Code"},
                    {"type": "code", "content": code},
                    {"type": "subheading", "content": "Review Feedback"},
                    {"type": "text", "content": feedback},
                    {
                        "type": "text",
                        "content": f"Reviewed: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    },
                ],
            }

            return self.document_service.create_rmdoc_from_content(
                url="",
                qr_path=None,
                content=content,
            )
        except Exception as e:
            self.logger.error(f"Error creating review document: {e}")
            return None

    async def _create_debug_document(
        self, code: str, error: str, debug_info: Dict[str, Any]
    ) -> Optional[str]:
        """Create a document with debugging results."""
        try:
            # Format debug info
            debug_text = ""
            if isinstance(debug_info, dict):
                if debug_info.get("error_explanation"):
                    debug_text += f"Explanation: {debug_info['error_explanation']}\n\n"
                if debug_info.get("root_cause"):
                    debug_text += f"Root Cause: {debug_info['root_cause']}\n\n"
                if debug_info.get("suggested_fix"):
                    debug_text += f"Suggested Fix: {debug_info['suggested_fix']}\n\n"
            else:
                debug_text = str(debug_info)

            content = {
                "title": "Debug Analysis",
                "sections": [
                    {"type": "heading", "content": "Debug Analysis"},
                    {"type": "subheading", "content": "Error Message"},
                    {"type": "text", "content": error},
                    {"type": "subheading", "content": "Original Code"},
                    {"type": "code", "content": code},
                    {"type": "subheading", "content": "Analysis"},
                    {"type": "text", "content": debug_text},
                ],
            }

            # Add fixed code if available
            if isinstance(debug_info, dict) and debug_info.get("fixed_code"):
                content["sections"].extend(
                    [
                        {"type": "subheading", "content": "Fixed Code"},
                        {"type": "code", "content": debug_info["fixed_code"]},
                    ]
                )

            content["sections"].append(
                {
                    "type": "text",
                    "content": f"Analyzed: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                }
            )

            return self.document_service.create_rmdoc_from_content(
                url="",
                qr_path=None,
                content=content,
            )
        except Exception as e:
            self.logger.error(f"Error creating debug document: {e}")
            return None

    async def _create_best_practices_document(
        self, query: str, advice: str, language: Optional[str]
    ) -> Optional[str]:
        """Create a document with best practices advice."""
        try:
            content = {
                "title": f"Best Practices: {query[:50]}",
                "sections": [
                    {"type": "heading", "content": "Best Practices"},
                    {"type": "subheading", "content": "Question"},
                    {"type": "text", "content": query},
                ],
            }

            if language:
                content["sections"].append(
                    {"type": "text", "content": f"Language: {language}"}
                )

            content["sections"].extend(
                [
                    {"type": "subheading", "content": "Advice"},
                    {"type": "text", "content": advice},
                    {
                        "type": "text",
                        "content": f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    },
                ]
            )

            return self.document_service.create_rmdoc_from_content(
                url="",
                qr_path=None,
                content=content,
            )
        except Exception as e:
            self.logger.error(f"Error creating best practices document: {e}")
            return None

    async def _create_summary_document(
        self, summary: str, focus: Optional[str]
    ) -> Optional[str]:
        """Create a document with technical summary."""
        try:
            content = {
                "title": f"Summary: {focus or 'Technical Content'}",
                "sections": [
                    {"type": "heading", "content": "Technical Summary"},
                ],
            }

            if focus:
                content["sections"].append(
                    {"type": "text", "content": f"Focus: {focus}"}
                )

            content["sections"].extend(
                [
                    {"type": "text", "content": summary},
                    {
                        "type": "text",
                        "content": f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    },
                ]
            )

            return self.document_service.create_rmdoc_from_content(
                url="",
                qr_path=None,
                content=content,
            )
        except Exception as e:
            self.logger.error(f"Error creating summary document: {e}")
            return None

    def _format_review_feedback(self, feedback: Any) -> str:
        """Format review feedback for display."""
        if isinstance(feedback, dict):
            formatted = ""

            if feedback.get("summary"):
                formatted += f"Summary:\n{feedback['summary']}\n\n"

            if feedback.get("issues"):
                formatted += "Issues:\n"
                for issue in feedback["issues"]:
                    formatted += f"• {issue}\n"
                formatted += "\n"

            if feedback.get("improvements"):
                formatted += "Improvements:\n"
                for improvement in feedback["improvements"]:
                    formatted += f"• {improvement}\n"
                formatted += "\n"

            if feedback.get("best_practices"):
                formatted += "Best Practices:\n"
                for practice in feedback["best_practices"]:
                    formatted += f"• {practice}\n"
                formatted += "\n"

            # Add raw feedback if no structured data
            if not formatted and feedback.get("raw_feedback"):
                formatted = feedback["raw_feedback"]

            return formatted or "No feedback available"
        else:
            return str(feedback)

    def _cache_result(self, operation: str, key: str, result: Any):
        """Cache a result for future reference."""
        try:
            cache_file = self.cache_path / f"{operation}_{hash(key)}.json"
            cache_data = {
                "operation": operation,
                "key": key,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }

            with open(cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)

        except Exception as e:
            self.logger.warning(f"Failed to cache result: {e}")

    async def _store_in_knowledge_graph(self, operation: str, prompt: str, result: Any):
        """Store coding activity in knowledge graph."""
        try:
            if not self.knowledge_graph:
                return

            # Create entity for the coding activity
            entity_name = f"Code_{operation}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            observations = [
                f"Operation: {operation}",
                f"Prompt: {prompt[:200]}",  # Truncate long prompts
                f"Timestamp: {datetime.now().isoformat()}",
            ]

            # Add result details
            if isinstance(result, dict):
                if result.get("code"):
                    observations.append(
                        f"Generated code length: {len(result['code'])} characters"
                    )
                if result.get("language"):
                    observations.append(f"Language: {result['language']}")
                if result.get("session_id"):
                    observations.append(f"Session: {result['session_id']}")

            # Create entity
            await self.knowledge_graph.create_entity(
                name=entity_name,
                entity_type="CodingActivity",
                observations=observations,
            )

            # Link to session if available
            if isinstance(result, dict) and result.get("session_id"):
                await self.knowledge_graph.create_relation(
                    from_entity=entity_name,
                    to_entity=f"Session_{result['session_id']}",
                    relation_type="part_of",
                )

        except Exception as e:
            self.logger.warning(f"Failed to store in knowledge graph: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            **self.stats,
            "active_sessions": len(self.active_sessions),
            "cache_size": len(list(self.cache_path.glob("*.json"))),
        }

    def __repr__(self):
        """String representation of the agent."""
        return f"CloudCoderAgent(state={self.state.value}, stats={self.stats})"
