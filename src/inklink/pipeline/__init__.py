"""Processing pipeline for InkLink.

This package provides a modular pipeline for processing content.
"""

from inklink.pipeline.pipeline import Pipeline
from inklink.pipeline.processor import PipelineContext, Processor

__all__ = ["Processor", "PipelineContext", "Pipeline"]
