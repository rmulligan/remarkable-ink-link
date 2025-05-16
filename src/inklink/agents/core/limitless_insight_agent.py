"""LimitlessContextualInsightAgent for processing Limitless pendant data."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from inklink.adapters.limitless_adapter import LimitlessAdapter
from inklink.adapters.ollama_adapter import OllamaAdapter
from inklink.agents.base.agent import AgentConfig
from inklink.agents.base.mcp_integration import MCPCapability, MCPEnabledAgent
from inklink.agents.exceptions import AgentError
from inklink.services.limitless_life_log_service import LimitlessLifeLogService


class LimitlessContextualInsightAgent(MCPEnabledAgent):
    """Agent for providing contextual insights from Limitless pendant data."""

    def __init__(
        self,
        config: AgentConfig,
        limitless_adapter: LimitlessAdapter,
        ollama_adapter: OllamaAdapter,
        storage_path: Path,
        knowledge_graph_service=None,  # Optional dependency
    ):
        """Initialize the Limitless insight agent."""
        super().__init__(config)
        self.limitless_adapter = limitless_adapter
        self.ollama_adapter = ollama_adapter
        self.storage_path = storage_path

        # If knowledge graph service is provided, use it; otherwise, create one
        if knowledge_graph_service is None:
            from inklink.services.knowledge_graph_service import KnowledgeGraphService

            knowledge_graph_service = KnowledgeGraphService()

        self.life_log_service = LimitlessLifeLogService(
            limitless_adapter=limitless_adapter,
            knowledge_graph_service=knowledge_graph_service,
        )
        self._setup_mcp_capabilities()

        # Initialize analysis cache for efficient lookup
        self._analysis_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 minutes cache TTL

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
                description="Recall action items from spoken content",
                handler=self._handle_recall_action_items,
                input_schema={
                    "type": "object",
                    "properties": {
                        "time_period": {
                            "type": "string",
                            "description": "Time period to search",
                        },
                        "context": {
                            "type": "string",
                            "description": "Optional context filter",
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
                description="Find spoken context about a topic",
                handler=self._handle_find_context,
                input_schema={
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Topic to search for",
                        },
                        "time_period": {
                            "type": "string",
                            "description": "Optional time period filter",
                        },
                    },
                    "required": ["topic"],
                },
            )
        )

    async def _agent_logic(self) -> None:
        """Main agent logic - process new Limitless transcripts."""
        process_interval = 60 * 60  # Process every hour

        while not self._stop_event.is_set():
            try:
                # Process new transcripts
                await self._process_new_transcripts()

                # Sleep until next processing cycle
                await asyncio.sleep(process_interval)

            except asyncio.CancelledError:
                self.logger.info("Agent logic cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in agent logic: {e}")
                await asyncio.sleep(60)  # Short sleep on error

    async def _process_new_transcripts(self) -> None:
        """Process new transcripts from Limitless."""
        try:
            # Get transcripts from the last hour
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)

            transcripts = await self.life_log_service.sync_life_logs(
                start_time=start_time, end_time=end_time
            )

            if not transcripts:
                self.logger.debug("No new transcripts to process")
                return

            # Analyze each transcript
            for transcript in transcripts:
                await self._analyze_transcript(transcript)

        except Exception as e:
            self.logger.error(f"Error processing transcripts: {e}")
            raise AgentError(f"Failed to process transcripts: {e}")

    async def _analyze_transcript(self, transcript: Dict[str, Any]) -> None:
        """Analyze a single transcript for insights."""
        try:
            # Extract text content
            text = transcript.get("transcript", "")
            if not text:
                return

            # Generate analysis using Ollama
            analysis_prompt = f"""
            Analyze the following transcript and extract:
            1. Key topics discussed
            2. Action items or commitments
            3. Important context or insights

            Transcript:
            {text[:2000]}  # Limit to first 2000 chars

            Provide the analysis in JSON format with keys: topics, action_items, insights
            """

            response = await self.ollama_adapter.query(analysis_prompt)

            try:
                analysis = json.loads(response)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a simple structure
                analysis = {"topics": [], "action_items": [], "insights": response}

            # Store analysis
            analysis_path = (
                self.storage_path
                / "analyses"
                / f"{transcript.get('id', 'unknown')}.json"
            )
            analysis_path.parent.mkdir(parents=True, exist_ok=True)

            with open(analysis_path, "w") as f:
                json.dump(
                    {
                        "transcript_id": transcript.get("id"),
                        "timestamp": transcript.get("timestamp"),
                        "analysis": analysis,
                    },
                    f,
                    indent=2,
                )

        except Exception as e:
            self.logger.error(f"Error analyzing transcript: {e}")

    def _refresh_analysis_cache(self) -> None:
        """Refresh the analysis cache if expired."""
        now = datetime.now()
        if (
            self._cache_timestamp is None
            or (now - self._cache_timestamp).total_seconds() > self._cache_ttl
        ):

            self._analysis_cache = {}
            analyses_dir = self.storage_path / "analyses"

            if analyses_dir.exists():
                # Index all analysis files once
                for analysis_file in analyses_dir.glob("*.json"):
                    try:
                        with open(analysis_file) as f:
                            data = json.load(f)
                            file_id = analysis_file.stem
                            self._analysis_cache[file_id] = data
                    except Exception as e:
                        self.logger.error(
                            f"Error loading analysis {analysis_file}: {e}"
                        )

            self._cache_timestamp = now

    async def _handle_get_spoken_summary(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle get spoken summary request."""
        time_period = params["time_period"]
        topic = params.get("topic")

        # Convert time period to datetime range
        end_time = datetime.now()
        if time_period == "last_24_hours":
            start_time = end_time - timedelta(hours=24)
        elif time_period == "yesterday":
            start_time = end_time - timedelta(days=1)
            start_time = start_time.replace(hour=0, minute=0, second=0)
            end_time = start_time + timedelta(days=1)
        else:
            # Default to last 24 hours
            start_time = end_time - timedelta(hours=24)

        # Get transcripts for the period
        transcripts = await self.life_log_service.sync_life_logs(
            start_time=start_time, end_time=end_time
        )

        # Filter by topic if provided
        if topic:
            transcripts = [
                t
                for t in transcripts
                if topic.lower() in t.get("transcript", "").lower()
            ]

        # Generate summary
        if not transcripts:
            return {"summary": "No spoken content found for the specified period."}

        combined_text = "\n".join(
            [t.get("transcript", "") for t in transcripts[:5]]
        )  # Limit to 5

        summary_prompt = f"""
        Summarize the following spoken content{' about ' + topic if topic else ''}:

        {combined_text[:3000]}

        Provide a concise summary highlighting key points and themes.
        """

        summary = await self.ollama_adapter.query(summary_prompt)

        return {
            "summary": summary,
            "transcript_count": len(transcripts),
            "time_period": f"{start_time.isoformat()} to {end_time.isoformat()}",
        }

    async def _handle_recall_action_items(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle recall action items request."""
        # Refresh cache if needed
        self._refresh_analysis_cache()

        action_items = []
        time_period = params.get("time_period")
        context_filter = params.get("context")

        # Filter by time period if provided
        end_time = datetime.now()
        start_time = None

        if time_period == "last_24_hours":
            start_time = end_time - timedelta(hours=24)
        elif time_period == "last_week":
            start_time = end_time - timedelta(days=7)

        # Extract action items from cached analyses
        for data in self._analysis_cache.values():
            # Check time filter
            if start_time and "timestamp" in data:
                try:
                    analysis_time = datetime.fromisoformat(data["timestamp"])
                    if analysis_time < start_time:
                        continue
                except ValueError:
                    # Skip entries with invalid timestamps
                    self.logger.debug(
                        f"Invalid timestamp format: {data.get('timestamp')}"
                    )

            if "analysis" in data and "action_items" in data["analysis"]:
                items = data["analysis"]["action_items"]
                # Apply context filter if provided
                if context_filter:
                    items = [
                        i for i in items if context_filter.lower() in str(i).lower()
                    ]
                action_items.extend(items)

        return {"action_items": action_items}

    async def _handle_find_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle find context request."""
        topic = params["topic"]
        time_period = params.get("time_period")

        # Refresh cache if needed
        self._refresh_analysis_cache()

        # Filter by time period if provided
        end_time = datetime.now()
        start_time = None

        if time_period == "last_24_hours":
            start_time = end_time - timedelta(hours=24)
        elif time_period == "last_week":
            start_time = end_time - timedelta(days=7)

        contexts = []
        for data in self._analysis_cache.values():
            # Check time filter
            if start_time and "timestamp" in data:
                try:
                    analysis_time = datetime.fromisoformat(data["timestamp"])
                    if analysis_time < start_time:
                        continue
                except ValueError:
                    # Skip entries with invalid timestamps
                    self.logger.debug(
                        f"Invalid timestamp format: {data.get('timestamp')}"
                    )

            if topic.lower() in str(data).lower():
                contexts.append(
                    {
                        "timestamp": data.get("timestamp"),
                        "relevance": (
                            "high"
                            if topic.lower() in str(data.get("analysis", {})).lower()
                            else "medium"
                        ),
                        "content": data.get("analysis"),
                    }
                )

        # Sort by relevance and timestamp
        contexts.sort(
            key=lambda x: (x["relevance"] == "high", x.get("timestamp", "")),
            reverse=True,
        )
        return {"contexts": contexts[:10]}  # Limit to 10 most relevant
