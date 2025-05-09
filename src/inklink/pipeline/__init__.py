"""Processing pipeline for InkLink.

This package provides a modular pipeline for processing content.
"""

from inklink.pipeline.processor import Processor, PipelineContext
from inklink.pipeline.pipeline import Pipeline

__all__ = ['Processor', 'PipelineContext', 'Pipeline']