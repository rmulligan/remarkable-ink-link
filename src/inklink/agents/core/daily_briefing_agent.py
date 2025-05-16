"""DailyBriefingAgent for generating personalized daily summaries."""

import asyncio
import json
from datetime import datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional

from inklink.adapters.ollama_adapter_enhanced import OllamaAdapter
from inklink.adapters.remarkable_adapter import RemarkableAdapter
from inklink.agents.base.agent import AgentConfig
from inklink.agents.exceptions import AgentError
from inklink.agents.base.mcp_integration import MCPCapability, MCPEnabledAgent
from inklink.services.remarkable_service import RemarkableService


class DailyBriefingAgent(MCPEnabledAgent):
    """Agent for generating daily briefings with Limitless context."""

    def __init__(
        self,
        config: AgentConfig,
        ollama_adapter: OllamaAdapter,
        remarkable_adapter: RemarkableAdapter,
        storage_path: Path,
        briefing_time: time = time(6, 0),
    ):  # Default 6 AM
        """Initialize the daily briefing agent."""
        super().__init__(config)
        self.ollama_adapter = ollama_adapter
        self.remarkable_adapter = remarkable_adapter
        self.storage_path = storage_path
        self.briefing_time = briefing_time
        self.remarkable_service = RemarkableService(remarkable_adapter)
        self._setup_mcp_capabilities()
        self._last_briefing_date: Optional[datetime] = None

    def _setup_mcp_capabilities(self) -> None:
        """Set up MCP capabilities for daily briefings."""
        # Generate briefing
        self.register_mcp_capability(
            MCPCapability(
                name="generate_briefing",
                description="Generate a daily briefing",
                handler=self._handle_generate_briefing,
                input_schema={
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "format": "date"},
                        "include_limitless": {"type": "boolean", "default": True},
                        "include_calendar": {"type": "boolean", "default": True},
                        "include_email": {"type": "boolean", "default": True},
                    },
                },
            )
        )

        # Get briefing status
        self.register_mcp_capability(
            MCPCapability(
                name="get_briefing_status",
                description="Get status of daily briefing generation",
                handler=self._handle_get_briefing_status,
            )
        )

    async def _agent_logic(self) -> None:
        """Main agent logic - check for briefing time."""
        while not self._stop_event.is_set():
            try:
                now = datetime.now()

                # Check if it's time for the daily briefing
                if now.time() >= self.briefing_time and (
                    self._last_briefing_date is None
                    or self._last_briefing_date.date() < now.date()
                ):

                    await self._generate_daily_briefing()
                    self._last_briefing_date = now

                # Wait for next check (1 minute)
                await asyncio.sleep(60)

            except AgentError as e:
                self.logger.error(f"Agent error: {e}")
                await asyncio.sleep(60)
            except Exception as e:
                self.logger.error(f"Unexpected error in agent logic: {e}")
                await asyncio.sleep(60)

    async def _generate_daily_briefing(self) -> Dict[str, Any]:
        """Generate the daily briefing."""
        self.logger.info("Generating daily briefing")

        try:
            # Gather data from various sources
            briefing_data = await self._gather_briefing_data()

            # Generate briefing content
            briefing_content = await self._create_briefing_content(briefing_data)

            # Create reMarkable template
            template_path = await self._create_remarkable_template(briefing_content)

            # Upload to reMarkable
            if template_path:
                await self.remarkable_service.upload_document(
                    template_path,
                    f"Daily Briefing - {datetime.now().strftime('%Y-%m-%d')}",
                )

            # Store briefing
            briefing_record = {
                "date": datetime.now().isoformat(),
                "content": briefing_content,
                "data": briefing_data,
                "template_path": str(template_path) if template_path else None,
            }

            record_path = (
                self.storage_path
                / "briefings"
                / f"{datetime.now().strftime('%Y%m%d')}.json"
            )
            record_path.parent.mkdir(parents=True, exist_ok=True)

            with open(record_path, "w") as f:
                json.dump(briefing_record, f, indent=2)

            return briefing_record

        except AgentError as e:
            self.logger.error(f"Agent error generating daily briefing: {e}")
            return {"error": str(e)}
        except Exception as e:
            self.logger.error(f"Unexpected error generating daily briefing: {e}")
            return {"error": str(e)}

    async def _gather_briefing_data(self) -> Dict[str, Any]:
        """Gather data from various sources for the briefing."""
        data = {}

        # Get Limitless context (via MCP to LimitlessContextualInsightAgent)
        try:
            limitless_response = await self.send_mcp_message(
                target="agent_limitless_insight",
                capability="get_spoken_summary",
                data={"time_period": "last_24_hours"},
            )
            data["limitless_summary"] = limitless_response.get("summary")

            # Get action items
            action_response = await self.send_mcp_message(
                target="agent_limitless_insight",
                capability="recall_spoken_action_items",
                data={"time_period": "last_24_hours"},
            )
            data["spoken_action_items"] = action_response.get("action_items", [])

        except Exception as e:
            self.logger.error(f"Error getting Limitless data: {e}")
            data["limitless_summary"] = "Unable to retrieve Limitless data"
            data["spoken_action_items"] = []

        # Get calendar events (placeholder - would integrate with Proton Calendar)
        data["calendar_events"] = await self._get_calendar_events()

        # Get email summary (placeholder - would integrate with ProtonMail)
        data["email_summary"] = await self._get_email_summary()

        # Get weather (could integrate with weather service)
        data["weather"] = await self._get_weather_forecast()

        return data

    async def _create_briefing_content(self, data: Dict[str, Any]) -> str:
        """Create the briefing content using Ollama."""
        # Validate configuration
        if not self.config.ollama_model:
            raise AgentError("Ollama model not configured")

        # Prepare the prompt
        prompt = f"""
        Create a comprehensive daily briefing based on the following information:

        SPOKEN CONTEXT (Last 24 hours):
        {data.get('limitless_summary', 'No spoken context available')}

        ACTION ITEMS FROM SPEECH:
        {json.dumps(data.get('spoken_action_items', []), indent=2)}

        TODAY'S CALENDAR:
        {json.dumps(data.get('calendar_events', []), indent=2)}

        EMAIL SUMMARY:
        {data.get('email_summary', 'No email summary available')}

        WEATHER:
        {data.get('weather', 'Weather information unavailable')}

        Please create a well-structured daily briefing that:
        1. Highlights the most important items for today
        2. Includes spoken commitments and action items
        3. Provides a clear schedule overview
        4. Summarizes key emails that need attention
        5. Includes weather information
        6. Ends with a motivational note

        Format the briefing for easy reading on a reMarkable tablet.
        """

        # Generate briefing using Ollama
        briefing = await self.ollama_adapter.query(self.config.ollama_model, prompt)

        return briefing

    async def _create_remarkable_template(self, content: str) -> Optional[Path]:
        """Create a reMarkable template for the briefing."""
        try:
            # Create template structure
            template = {
                "type": "daily_briefing",
                "title": f"Daily Briefing - {datetime.now().strftime('%A, %B %d, %Y')}",
                "sections": [],
            }

            # Parse content into sections
            sections = content.split("\n\n")
            for i, section in enumerate(sections):
                if section.strip():
                    template["sections"].append(
                        {
                            "id": f"section_{i}",
                            "content": section.strip(),
                            "type": "text",
                        }
                    )

            # Save template
            template_path = (
                self.storage_path
                / "templates"
                / f"briefing_{datetime.now().strftime('%Y%m%d')}.json"
            )
            template_path.parent.mkdir(parents=True, exist_ok=True)

            with open(template_path, "w") as f:
                json.dump(template, f, indent=2)

            return template_path

        except Exception as e:
            self.logger.error(f"Error creating template: {e}")
            return None

    @staticmethod
    async def _get_calendar_events() -> List[Dict[str, Any]]:
        """Get today's calendar events (placeholder)."""
        # This would integrate with Proton Calendar
        return [
            {"time": "09:00", "title": "Team Standup", "duration": "30 minutes"},
            {"time": "14:00", "title": "Project Review", "duration": "1 hour"},
        ]

    @staticmethod
    async def _get_email_summary() -> str:
        """Get email summary (placeholder)."""
        # This would integrate with ProtonMail
        return "3 unread emails requiring attention: Project update from Sarah, Code review request, Meeting rescheduling"

    @staticmethod
    async def _get_weather_forecast() -> str:
        """Get weather forecast (placeholder)."""
        # This could integrate with a weather API
        return "Partly cloudy, 72°F (22°C), 20% chance of rain"

    async def _handle_generate_briefing(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle manual briefing generation request."""
        # Generate briefing for today
        return await self._generate_daily_briefing()

    async def _handle_get_briefing_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle briefing status request."""
        return {
            "last_briefing_date": (
                self._last_briefing_date.isoformat()
                if self._last_briefing_date
                else None
            ),
            "next_briefing_time": self.briefing_time.isoformat(),
            "status": "running" if self.state == "running" else "stopped",
        }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests to the agent."""
        request_type = request.get("type")

        if request_type == "generate_briefing":
            return await self._generate_daily_briefing()

        if request_type == "set_briefing_time":
            new_time = request.get("time")
            if new_time:
                self.briefing_time = time.fromisoformat(new_time)
                return {"status": "updated", "new_time": new_time}

        else:
            return {"error": f"Unknown request type: {request_type}"}
