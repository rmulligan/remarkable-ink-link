"""LimitlessContextualInsightAgent for processing Limitless pendant data."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from inklink.adapters.limitless_adapter import LimitlessAdapter
from inklink.adapters.ollama_adapter import OllamaAdapter
from inklink.agents.base.agent import AgentConfig, AgentState
from inklink.agents.base.mcp_integration import MCPCapability, MCPEnabledAgent
from inklink.services.limitless_life_log_service import LimitlessLifeLogService


class LimitlessContextualInsightAgent(MCPEnabledAgent):
    """Agent for providing contextual insights from Limitless pendant data."""

    def __init__(
        self,
        config: AgentConfig,
        limitless_adapter: LimitlessAdapter,
        ollama_adapter: OllamaAdapter,
        storage_path: Path,
    ):
        """Initialize the Limitless insight agent."""
        super().__init__(config)
        self.limitless_adapter = limitless_adapter
        self.ollama_adapter = ollama_adapter
        self.storage_path = storage_path
        self.life_log_service = LimitlessLifeLogService(limitless_adapter, storage_path)
        self._setup_mcp_capabilities()

    def _setup_mcp_capabilities(self) -> None:
        """Set up MCP capabilities specific to Limitless insights."""
        # Get spoken summary
        self.register_mcp_capability(
            MCPCapability(
                name="get_spoken_summary",
                description="Get a summary of spoken content for a time period",
                handler=self._handle_get_spoken_summary,
                input_schema={
                    "type": "object",
                    "properties": {
                        "time_period": {
                            "type": "string",
                            "description": "Time period (e.g., 'last_24_hours', 'yesterday')",
                        },
                        "topic": {
                            "type": "string",
                            "description": "Optional topic filter",
                        },
                    },
                    "required": ["time_period"],
                },
            )
        )

        # Recall spoken action items
        self.register_mcp_capability(
            MCPCapability(
                name="recall_spoken_action_items",
                description="Recall action items mentioned in speech",
                handler=self._handle_recall_action_items,
                input_schema={
                    "type": "object",
                    "properties": {
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "time_period": {
                            "type": "string",
                            "description": "Time period to search",
                        },
                    },
                    "required": ["time_period"],
                },
            )
        )

        # Find spoken context
        self.register_mcp_capability(
            MCPCapability(
                name="find_spoken_context",
                description="Find context about a specific topic from speech",
                handler=self._handle_find_spoken_context,
                input_schema={
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Topic to search for",
                        },
                        "time_period": {
                            "type": "string",
                            "description": "Optional time period",
                        },
                    },
                    "required": ["topic"],
                },
            )
        )

    async def _agent_logic(self) -> None:
        """Main agent logic - periodically process new Limitless data."""
        while not self._stop_event.is_set():
            try:
                # Check for new transcripts
                await self._process_new_transcripts()

                # Wait before next check (5 minutes)
                await asyncio.sleep(300)

            except Exception as e:
                self.logger.error(f"Error in agent logic: {e}")
                await asyncio.sleep(60)  # Shorter wait on error

    async def _process_new_transcripts(self) -> None:
        """Process any new transcripts from Limitless."""
        try:
            # Get latest transcripts
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=5)

            transcripts = await self.life_log_service.get_transcripts(
                start_time, end_time
            )

            if transcripts:
                self.logger.info(f"Processing {len(transcripts)} new transcripts")

                # Process with personalized model if available
                if self.config.ollama_model:
                    for transcript in transcripts:
                        await self._analyze_transcript(transcript)

        except Exception as e:
            self.logger.error(f"Error processing transcripts: {e}")

    async def _analyze_transcript(self, transcript: Dict[str, Any]) -> None:
        """Analyze a single transcript for insights."""
        try:
            # Extract action items
            action_items_prompt = (
                "Extract any action items, commitments, or tasks mentioned in this transcript. "
                "Format as a list with context about when it was mentioned."
            )

            action_items = await self.ollama_adapter.query(
                self.config.ollama_model,
                action_items_prompt,
                context=transcript.get("text", ""),
            )

            # Extract key topics
            topics_prompt = (
                "Identify the main topics discussed in this transcript. "
                "List the topics with brief descriptions."
            )

            topics = await self.ollama_adapter.query(
                self.config.ollama_model,
                topics_prompt,
                context=transcript.get("text", ""),
            )

            # Store analysis results
            analysis = {
                "transcript_id": transcript.get("id"),
                "timestamp": transcript.get("timestamp"),
                "action_items": action_items,
                "topics": topics,
                "processed_at": datetime.now().isoformat(),
            }

            analysis_path = (
                self.storage_path / "analyses" / f"{transcript.get('id')}.json"
            )
            analysis_path.parent.mkdir(parents=True, exist_ok=True)

            with open(analysis_path, "w") as f:
                json.dump(analysis, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error analyzing transcript: {e}")

    async def _handle_get_spoken_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request for spoken content summary."""
        time_period = data.get("time_period")
        topic = data.get("topic")

        try:
            # Parse time period
            end_time = datetime.now()
            if time_period == "last_24_hours":
                start_time = end_time - timedelta(hours=24)
            elif time_period == "yesterday":
                start_time = end_time - timedelta(days=1)
                start_time = start_time.replace(hour=0, minute=0, second=0)
                end_time = start_time + timedelta(days=1)
            else:
                start_time = end_time - timedelta(hours=24)  # Default

            # Get transcripts
            transcripts = await self.life_log_service.get_transcripts(
                start_time, end_time
            )

            if not transcripts:
                return {
                    "summary": "No spoken content found for the specified time period."
                }

            # Create summary prompt
            combined_text = " ".join([t.get("text", "") for t in transcripts])

            if topic:
                prompt = f"Summarize discussions about '{topic}' from the following conversations:"
            else:
                prompt = (
                    "Provide a comprehensive summary of the following conversations:"
                )

            # Generate summary using Ollama
            summary = await self.ollama_adapter.query(
                self.config.ollama_model or "llama3:8b", prompt, context=combined_text
            )

            return {
                "summary": summary,
                "time_period": time_period,
                "transcript_count": len(transcripts),
                "topic": topic,
            }

        except Exception as e:
            self.logger.error(f"Error generating spoken summary: {e}")
            return {"error": str(e)}

    async def _handle_recall_action_items(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to recall spoken action items."""
        time_period = data.get("time_period")
        keywords = data.get("keywords", [])

        try:
            # Parse time period (similar to summary)
            end_time = datetime.now()
            if time_period == "last_24_hours":
                start_time = end_time - timedelta(hours=24)
            else:
                start_time = end_time - timedelta(hours=24)  # Default

            # Get analyses
            analyses = []
            analysis_dir = self.storage_path / "analyses"

            if analysis_dir.exists():
                for file_path in analysis_dir.glob("*.json"):
                    with open(file_path, "r") as f:
                        analysis = json.load(f)

                    # Check if within time period
                    timestamp = datetime.fromisoformat(analysis["timestamp"])
                    if start_time <= timestamp <= end_time:
                        analyses.append(analysis)

            # Filter action items
            action_items = []
            for analysis in analyses:
                items = analysis.get("action_items", [])

                # Filter by keywords if provided
                if keywords:
                    filtered_items = []
                    for item in items:
                        if any(
                            keyword.lower() in str(item).lower() for keyword in keywords
                        ):
                            filtered_items.append(item)
                    items = filtered_items

                action_items.extend(items)

            return {
                "action_items": action_items,
                "time_period": time_period,
                "keywords": keywords,
                "count": len(action_items),
            }

        except Exception as e:
            self.logger.error(f"Error recalling action items: {e}")
            return {"error": str(e)}

    async def _handle_find_spoken_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to find spoken context about a topic."""
        topic = data.get("topic")
        time_period = data.get("time_period", "last_7_days")

        try:
            # Parse time period
            end_time = datetime.now()
            if time_period == "last_24_hours":
                start_time = end_time - timedelta(hours=24)
            elif time_period == "last_7_days":
                start_time = end_time - timedelta(days=7)
            else:
                start_time = end_time - timedelta(days=7)  # Default

            # Get relevant transcripts
            transcripts = await self.life_log_service.get_transcripts(
                start_time, end_time
            )

            # Filter by topic
            relevant_segments = []
            for transcript in transcripts:
                text = transcript.get("text", "")

                # Simple keyword matching (could be enhanced with semantic search)
                if topic.lower() in text.lower():
                    # Extract surrounding context
                    sentences = text.split(".")
                    for i, sentence in enumerate(sentences):
                        if topic.lower() in sentence.lower():
                            # Get context (previous and next sentence)
                            context_start = max(0, i - 1)
                            context_end = min(len(sentences), i + 2)
                            context = ". ".join(sentences[context_start:context_end])

                            relevant_segments.append(
                                {
                                    "context": context,
                                    "timestamp": transcript.get("timestamp"),
                                    "transcript_id": transcript.get("id"),
                                }
                            )

            # Generate insight using Ollama
            if relevant_segments:
                contexts = [seg["context"] for seg in relevant_segments]
                prompt = (
                    f"Based on these conversations about '{topic}', provide key insights "
                    "and important points discussed:"
                )

                insights = await self.ollama_adapter.query(
                    self.config.ollama_model or "llama3:8b",
                    prompt,
                    context="\n\n".join(contexts),
                )
            else:
                insights = f"No discussions found about '{topic}' in the specified time period."

            return {
                "topic": topic,
                "time_period": time_period,
                "insights": insights,
                "context_count": len(relevant_segments),
                "contexts": relevant_segments[:5],  # Return first 5 contexts
            }

        except Exception as e:
            self.logger.error(f"Error finding spoken context: {e}")
            return {"error": str(e)}

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests to the agent."""
        request_type = request.get("type")

        if request_type == "process_transcript":
            transcript = request.get("transcript")
            await self._analyze_transcript(transcript)
            return {"status": "processed"}

        elif request_type == "get_insights":
            topic = request.get("topic")
            return await self._handle_find_spoken_context({"topic": topic})

        else:
            return {"error": f"Unknown request type: {request_type}"}
