"""Upload processor for InkLink.

This module provides a processor for uploading documents to reMarkable.
"""

import logging
from typing import Dict, Any, Optional

from inklink.pipeline.processor import Processor, PipelineContext
from inklink.services.interfaces import IRemarkableService

logger = logging.getLogger(__name__)


class UploadProcessor(Processor):
    """Uploads documents to reMarkable Cloud."""
    
    def __init__(self, remarkable_service: IRemarkableService):
        """
        Initialize with reMarkable service.
        
        Args:
            remarkable_service: reMarkable service for uploading documents
        """
        self.remarkable_service = remarkable_service
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process the context by uploading a document to reMarkable.
        
        Args:
            context: Pipeline context with document path
            
        Returns:
            Updated pipeline context with upload result
        """
        # Skip if no document path or there are errors
        if not context.get_artifact("rm_path") or context.has_errors():
            return context
            
        try:
            # Get parameters from context
            rm_path = context.get_artifact("rm_path", "")
            title = context.get_artifact("document_title", context.url)
            
            # Upload to reMarkable
            success, message = self.remarkable_service.upload(rm_path, title)
            
            # Add upload result to context
            context.add_artifact("upload_success", success)
            context.add_artifact("upload_message", message)
            
            if success:
                logger.info(f"Document uploaded successfully: {title}")
            else:
                logger.error(f"Failed to upload document: {message}")
                context.add_error(f"Upload failed: {message}", processor=str(self))
                
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}")
            context.add_error(f"Failed to upload document: {str(e)}", processor=str(self))
            
        return context