#!/usr/bin/env python
"""
Claude Vision Adapter for handwriting recognition.

This adapter uses Claude's vision capabilities through the 'claude' CLI tool
to recognize handwritten text from rendered images of reMarkable notebook pages.
"""

import os
import logging
import tempfile
import json
import subprocess
from typing import Dict, List, Optional, Tuple, Union, Any

from .adapter import Adapter


class ClaudeVisionAdapter(Adapter):
    """
    Adapter for Claude's vision capabilities to process handwritten notes.
    
    This adapter uses Claude's CLI tool to analyze rendered PNG images 
    of reMarkable notebook pages.
    """
    
    def __init__(
        self,
        claude_command: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the Claude Vision adapter.
        
        Args:
            claude_command: Command to invoke Claude CLI (defaults to 'claude')
            model: Claude model specification (if needed)
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Get command from arguments or environment
        self.claude_command = claude_command or os.environ.get("CLAUDE_COMMAND", "/home/ryan/.claude/local/claude")
        self.model = model or os.environ.get("CLAUDE_MODEL", "")
        
        # Model flag for command if specified
        self.model_flag = f"--model {self.model}" if self.model else ""
        
        # Check if claude CLI is available
        self._check_claude_availability()
    
    def _check_claude_availability(self) -> bool:
        """
        Check if the Claude CLI tool is available.
        
        Returns:
            True if available, False otherwise
        """
        try:
            result = subprocess.run(
                [self.claude_command, "--version"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                self.logger.info(f"Claude CLI available: {result.stdout.strip()}")
                return True
            else:
                self.logger.warning(f"Claude CLI check failed: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to check Claude CLI availability: {e}")
            return False
    
    def is_available(self) -> bool:
        """
        Check if the Claude Vision adapter is available.
        
        Returns:
            True if the adapter can use the Claude CLI tool
        """
        return self._check_claude_availability()
        
    def ping(self) -> bool:
        """
        Check if the service is responding.
        
        Returns:
            True if the service is available, False otherwise
        """
        return self._check_claude_availability()
    
    def process_image(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        content_type: str = "text",
        max_tokens: int = 4000,
    ) -> Tuple[bool, Union[str, Dict]]:
        """
        Process an image with Claude's vision capabilities via CLI.
        
        Args:
            image_path: Path to the image file
            prompt: Custom prompt for Claude (default: transcribe handwritten text)
            content_type: Type of content in the image (text, math, diagram)
            max_tokens: Maximum number of tokens for Claude's response
            
        Returns:
            Tuple of (success, result)
            - If successful, result is the extracted text
            - If unsuccessful, result is an error message or dict
        """
        if not os.path.exists(image_path):
            return False, f"Image file not found: {image_path}"
        
        # Default prompt based on content type
        if prompt is None:
            if content_type.lower() == "math":
                prompt = "Please transcribe the handwritten mathematical content in this image. Represent equations using LaTeX notation."
            elif content_type.lower() == "diagram":
                prompt = "Please describe the diagram or drawing in this image. Identify key elements, connections, and any labeled components."
            else:  # Default text prompt
                prompt = "Please transcribe the handwritten text in this image. Maintain the formatting structure as much as possible."
        
        try:
            # Create a temporary file for the result
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as temp_file:
                result_path = temp_file.name
                
                # Build command: claude <image_path> "prompt" > result_file
                max_tokens_flag = f"--max-tokens {max_tokens}"
                command = f'{self.claude_command} {self.model_flag} {max_tokens_flag} "{image_path}" "{prompt}" > {result_path}'
                
                # Execute the command through shell due to redirection
                result = subprocess.run(
                    command, 
                    shell=True, 
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    return False, f"Claude CLI failed: {result.stderr}"
                
                # Read the result
                with open(result_path, 'r') as f:
                    claude_response = f.read()
                
                # Delete temporary file
                try:
                    os.unlink(result_path)
                except Exception:
                    pass
                
                return True, claude_response.strip()
                
        except Exception as e:
            self.logger.error(f"Error processing image with Claude CLI: {e}")
            return False, f"Error processing image: {str(e)}"
    
    def process_multiple_images(
        self,
        image_paths: List[str],
        prompt: Optional[str] = None,
        maintain_context: bool = True,
        max_tokens: int = 8000,
    ) -> Tuple[bool, Union[str, Dict]]:
        """
        Process multiple images with Claude's vision capabilities via CLI.
        
        Args:
            image_paths: List of paths to image files
            prompt: Custom prompt for Claude
            maintain_context: Whether to process images as a single context
            max_tokens: Maximum number of tokens for Claude's response
            
        Returns:
            Tuple of (success, result)
        """
        # Verify all images exist
        for path in image_paths:
            if not os.path.exists(path):
                return False, f"Image file not found: {path}"
        
        # Default prompt for multiple images
        if prompt is None:
            if maintain_context:
                prompt = """
                I'm sharing multiple pages from a handwritten notebook.
                Please transcribe the content, maintaining context between pages.
                Treat these as continuous content from the same document.
                Clearly indicate where each page begins and ends by using "PAGE X:" markers.
                """
            else:
                prompt = """
                I'm sharing multiple pages from a handwritten notebook.
                Please transcribe each page separately, clearly indicating where each page begins and ends.
                """
        
        try:
            # Create a temporary file for the result
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as temp_file:
                result_path = temp_file.name
                
                # Build command with multiple images
                image_arguments = " ".join([f'"{path}"' for path in image_paths])
                max_tokens_flag = f"--max-tokens {max_tokens}"
                command = f'{self.claude_command} {self.model_flag} {max_tokens_flag} {image_arguments} "{prompt}" > {result_path}'
                
                # Execute the command
                result = subprocess.run(
                    command, 
                    shell=True, 
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    return False, f"Claude CLI failed: {result.stderr}"
                
                # Read the result
                with open(result_path, 'r') as f:
                    claude_response = f.read()
                
                # Delete temporary file
                try:
                    os.unlink(result_path)
                except Exception:
                    pass
                
                return True, claude_response.strip()
                
        except Exception as e:
            self.logger.error(f"Error processing multiple images with Claude CLI: {e}")
            return False, f"Error processing images: {str(e)}"

    def safe_process_with_retries(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        content_type: str = "text",
        retries: int = 3
    ) -> Tuple[bool, Union[str, Dict]]:
        """
        Process an image with retries and error handling.
        
        Args:
            image_path: Path to the image file
            prompt: Custom prompt for Claude
            content_type: Type of content in the image
            retries: Number of retry attempts
            
        Returns:
            Tuple of (success, result)
        """
        import random
        import time
        
        attempt = 0
        
        while attempt < retries:
            try:
                result = self.process_image(image_path, prompt, content_type)
                return result
            except Exception as e:
                # Retry with exponential backoff
                delay = (2 ** attempt) + random.uniform(0, 1)
                self.logger.warning(f"Error, retrying in {delay:.2f} seconds (attempt {attempt+1}/{retries}): {e}")
                time.sleep(delay)
                attempt += 1
        
        return False, "Failed after multiple retry attempts"