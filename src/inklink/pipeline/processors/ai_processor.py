"""AI processing for InkLink.

This module provides a processor for AI-based content processing.
"""

import logging
from typing import Any, Dict, Optional

from inklink.pipeline.processor import PipelineContext, Processor
from inklink.services.ai_service import AIService

logger = logging.getLogger(__name__)


class AIProcessor(Processor):
    """Processes content with AI."""

    def __init__(self, ai_service: AIService):
        """
        Initialize with AI service.

        Args:
            ai_service: AI service for processing content
        """
        self.ai_service = ai_service

    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process the context with AI.

        Args:
            context: Pipeline context with content

        Returns:
            Updated pipeline context with AI-processed content
        """
        # Skip if no content or there are errors
        if not context.content or context.has_errors():
            return context

        try:
            # Extract main text for AI processing
            main_text = self._extract_main_text(context.content)

            # Extract context for AI
            ai_context = {k: v for k, v in context.content.items() if k != "content"}

            # Process with AI
            ai_response = self.ai_service.process_query(main_text, context=ai_context)

            # Add AI response to content
            context.content["ai_summary"] = ai_response

            # Add AI response to artifacts
            context.add_artifact("ai_summary", ai_response)

            logger.info("AI processing completed")

        except Exception as e:
            logger.error(f"Error in AI processing: {str(e)}")
            context.add_error(f"AI processing failed: {str(e)}", processor=str(self))

        return context

    def _extract_main_text(self, content: Dict[str, Any]) -> str:
        """
        Extract main text from content.

        Args:
            content: Content dictionary

        Returns:
            Extracted main text
        """
        main_text = ""

        if isinstance(content.get("content"), str):
            main_text = content["content"]
        elif isinstance(content.get("content"), list):
            # Join all text fields if structured as a list of dicts
            main_text = " ".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content["content"]
            )
        else:
            main_text = str(content)

        return main_text
