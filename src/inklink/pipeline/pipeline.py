"""Pipeline for processing content.

This module provides a pipeline for processing content through a series of processors.
"""

import logging
from typing import List, Dict, Any, Optional

from inklink.pipeline.processor import Processor, PipelineContext

logger = logging.getLogger(__name__)


class Pipeline:
    """Pipeline for processing content through a series of processors."""

    def __init__(self, processors: List[Processor] = None, name: str = "Pipeline"):
        """
        Initialize with processors.

        Args:
            processors: List of processors
            name: Pipeline name
        """
        self.processors = processors or []
        self.name = name

    def add_processor(self, processor: Processor) -> "Pipeline":
        """
        Add a processor to the pipeline.

        Args:
            processor: Processor to add

        Returns:
            Self for chaining
        """
        self.processors.append(processor)
        return self

    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process the context through the pipeline.

        Args:
            context: Pipeline context

        Returns:
            Processed context
        """
        logger.info(f"Starting pipeline: {self.name}")

        for processor in self.processors:
            try:
                logger.debug(f"Running processor: {processor}")
                context = processor.process(context)

                # Check for errors
                if context.has_errors():
                    logger.warning(f"Processor {processor} reported errors")
                    # Continue processing unless explicitly stopped

            except Exception as e:
                logger.error(f"Error in processor {processor}: {str(e)}")
                context.add_error(str(e), str(processor))

        logger.info(f"Pipeline {self.name} completed with {len(context.errors)} errors")
        return context

    def __str__(self) -> str:
        """
        Get string representation.

        Returns:
            Pipeline name and processor count
        """
        return f"{self.name} ({len(self.processors)} processors)"
