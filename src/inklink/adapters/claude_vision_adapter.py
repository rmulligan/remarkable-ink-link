#!/usr/bin/env python
"""
Claude Vision Adapter for handwriting recognition.

This adapter uses Claude's vision capabilities through the 'claude' CLI tool
to recognize handwritten text from rendered images of reMarkable notebook pages.
"""

import concurrent.futures
import logging
import os
import random
import subprocess
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

# PIL for image processing
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

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
        enable_preprocessing: bool = True,
        contrast_factor: float = 1.5,
        brightness_factor: float = 1.2,
        target_dpi: int = 300,
        apply_thresholding: bool = True,
        enable_parallel_processing: bool = True,
        max_parallel_workers: int = 4,
    ):
        """
        Initialize the Claude Vision adapter.

        Args:
            claude_command: Command to invoke Claude CLI (defaults to 'claude')
            model: Claude model specification (if needed)
            enable_preprocessing: Whether to enable image preprocessing
            contrast_factor: Factor to enhance contrast (default: 1.5)
            brightness_factor: Factor to enhance brightness (default: 1.2)
            target_dpi: Target DPI for image optimization (default: 300)
            apply_thresholding: Whether to apply thresholding for background removal
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)

        # Get command from arguments or environment
        self.claude_command = claude_command or os.environ.get(
            "CLAUDE_COMMAND", "/home/ryan/.claude/local/claude"
        )
        self.model = model or os.environ.get("CLAUDE_MODEL", "")

        # Model flag for command if specified
        self.model_flag = f"--model {self.model}" if self.model else ""

        # Image preprocessing settings
        self.enable_preprocessing = enable_preprocessing
        self.contrast_factor = contrast_factor
        self.brightness_factor = brightness_factor
        self.target_dpi = target_dpi
        self.apply_thresholding = apply_thresholding

        # Parallel processing settings
        self.enable_parallel_processing = enable_parallel_processing
        self.max_parallel_workers = max_parallel_workers

        # Check if claude CLI is available
        self._check_claude_availability()

    def _check_claude_availability(self) -> bool:
        """
        Check if the Claude CLI tool is available.

        Returns:
            True if available, False otherwise
        """
        try:
            # Split the command if it contains spaces
            # Remove -c flag if it's part of the command when checking version
            cmd = self.claude_command.replace(" -c", "").replace(" -r", "")
            cmd_parts = cmd.split() if " " in cmd else [cmd]
            result = subprocess.run(
                cmd_parts + ["--version"], capture_output=True, text=True
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

    def preprocess_image(
        self,
        image_path: str,
        content_type: str = "text",
    ) -> str:
        """
        Preprocess the image to optimize for Claude's vision model.

        This function performs:
        1. Contrast enhancement
        2. Background removal
        3. Image optimization based on content type

        Args:
            image_path: Path to the input image
            content_type: Type of content (text, math, diagram)

        Returns:
            Path to the preprocessed image
        """
        if not self.enable_preprocessing:
            return image_path

        try:
            # Create output filename with _preprocessed suffix
            filename, ext = os.path.splitext(image_path)
            output_path = f"{filename}_preprocessed{ext}"

            # Open the image
            img = Image.open(image_path)

            # Convert to RGB if needed (for consistency)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Apply content-specific preprocessing
            if content_type.lower() == "text":
                # For text: higher contrast, sharpening
                img = ImageEnhance.Contrast(img).enhance(self.contrast_factor)
                img = ImageEnhance.Brightness(img).enhance(self.brightness_factor)
                img = img.filter(ImageFilter.SHARPEN)

                # Apply thresholding for clear text if enabled
                if self.apply_thresholding:
                    # Convert to grayscale
                    img_gray = img.convert("L")
                    # Apply adaptive thresholding for better text extraction
                    # Using simple method here, could be improved with more sophisticated algorithms
                    threshold = np.mean(np.array(img_gray)) * 0.8
                    img = img_gray.point(lambda p: 255 if p > threshold else 0)

            elif content_type.lower() == "math":
                # For math: preserve details but enhance contrast
                img = ImageEnhance.Contrast(img).enhance(self.contrast_factor * 0.9)
                img = ImageEnhance.Brightness(img).enhance(self.brightness_factor)
                img = img.filter(ImageFilter.DETAIL)

            elif content_type.lower() == "diagram":
                # For diagrams: enhance edges and structure
                img = ImageEnhance.Contrast(img).enhance(self.contrast_factor * 0.8)
                img = img.filter(ImageFilter.EDGE_ENHANCE)

            # Ensure good resolution for Claude's vision model
            # Calculate current DPI based on image size
            width, height = img.size
            if width < 1000 or height < 1000:  # If image is small
                # Scale up to improve OCR results
                scale_factor = max(1, self.target_dpi / 72)  # Assuming 72 DPI as base
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                img = img.resize((new_width, new_height), Image.LANCZOS)

            # Save the preprocessed image
            img.save(output_path, quality=95)

            self.logger.info(f"Preprocessed image saved to {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Image preprocessing failed: {e}")
            # Return the original image if preprocessing fails
            return image_path

    def process_image(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        content_type: str = "text",
        max_tokens: int = 4000,
        preprocess: Optional[bool] = None,
    ) -> Tuple[bool, Union[str, Dict]]:
        """
        Process an image with Claude's vision capabilities via CLI.

        Args:
            image_path: Path to the image file
            prompt: Custom prompt for Claude (default: transcribe handwritten text)
            content_type: Type of content in the image (text, math, diagram)
            max_tokens: Maximum number of tokens for Claude's response
            preprocess: Whether to preprocess the image (overrides class setting)

        Returns:
            Tuple of (success, result)
            - If successful, result is the extracted text
            - If unsuccessful, result is an error message or dict
        """
        if not os.path.exists(image_path):
            return False, f"Image file not found: {image_path}"

        # Determine whether to preprocess
        should_preprocess = (
            preprocess if preprocess is not None else self.enable_preprocessing
        )

        # Preprocess the image if enabled
        processed_image_path = (
            self.preprocess_image(image_path, content_type)
            if should_preprocess
            else image_path
        )

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
            with tempfile.NamedTemporaryFile(
                mode="w+", suffix=".txt", delete=False
            ) as temp_file:
                result_path = temp_file.name

                # Build command: claude <image_path> "prompt" > result_file
                max_tokens_flag = f"--max-tokens {max_tokens}"
                command = f'{self.claude_command} {self.model_flag} {max_tokens_flag} "{processed_image_path}" "{prompt}" > {result_path}'

                # Execute the command through shell due to redirection
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True
                )

                if result.returncode != 0:
                    return False, f"Claude CLI failed: {result.stderr}"

                # Read the result
                with open(result_path, "r") as f:
                    claude_response = f.read()

                # Delete temporary file
                try:
                    os.unlink(result_path)
                except Exception:
                    pass
                return True, claude_response.strip()

        except Exception as e:
            self.logger.error(f"Error processing image with Claude CLI: {e}")

            # Clean up preprocessed image on error
            if should_preprocess and processed_image_path != image_path:
                try:
                    os.unlink(processed_image_path)
                except Exception:
                    pass

            return False, f"Error processing image: {str(e)}"

    def detect_content_type(self, image_path: str) -> str:
        """
        Attempt to detect the content type of an image (text, math, diagram).

        Args:
            image_path: Path to the image file

        Returns:
            Detected content type as string ("text", "math", or "diagram")
        """
        try:
            # Open the image
            img = Image.open(image_path)

            # Convert to grayscale for analysis
            # img_gray = img.convert("L")  # TODO: Remove if not used
            # img_array = np.array(img_gray)  # TODO: Remove if not needed

            # Simple heuristic detection:
            # 1. Calculate edge density (for diagrams)
            edge_img = img.filter(ImageFilter.FIND_EDGES)
            edge_array = np.array(edge_img.convert("L"))
            edge_density = np.mean(edge_array > 50) * 100  # Percentage of edge pixels

            # 2. Calculate line-like structures (for math)
            # horizontal_kernel = np.ones((1, 15), np.uint8)  # TODO: Remove if not needed
            # vertical_kernel = np.ones((15, 1), np.uint8)  # TODO: Remove if not needed

            # Simplified structural analysis
            # Higher values suggest more structured content like math
            structure_score = 0

            # Simplified density calculations
            if edge_density > 10:  # High edge density suggests diagram
                return "diagram"
            elif structure_score > 5:  # More structured content suggests math
                return "math"
            else:
                return "text"  # Default to text

        except Exception as e:
            self.logger.warning(
                f"Content type detection failed: {e}. Defaulting to 'text'"
            )
            return "text"  # Default to text on error

    def _process_single_image_for_batch(
        self,
        image_path: str,
        page_index: int,
        total_pages: int,
        content_type: Optional[str] = None,
        context: Optional[str] = None,
        preprocess: bool = True,
        max_tokens: int = 4000,
    ) -> Tuple[bool, Union[str, Dict]]:
        """
        Process a single image as part of a batch workflow.
        Used internally by process_multiple_images when parallel processing.

        Args:
            image_path: Path to the image file
            page_index: Index of this page in the sequence
            total_pages: Total number of pages in the sequence
            content_type: Type of content, or None to auto-detect
            context: Optional context from previous pages
            preprocess: Whether to preprocess the image
            max_tokens: Maximum tokens for response

        Returns:
            Tuple of (success, result)
        """
        # Auto-detect content type if not specified
        if content_type is None:
            content_type = self.detect_content_type(image_path)
            self.logger.info(
                f"Auto-detected content type for page {page_index + 1}: {content_type}"
            )

        # Build page-specific prompt with context awareness
        page_prompt = f"""
        Please transcribe the handwritten content on this page ({page_index + 1} of {total_pages}).
        This is a {content_type} document.
        """

        # Add context from previous pages if available
        if context:
            page_prompt += f"""
            For context, here is content from previous pages:
            {context}

            Continue the transcription from where this left off.
            """

        # Process the image
        success, result = self.process_image(
            image_path=image_path,
            prompt=page_prompt,
            content_type=content_type,
            max_tokens=max_tokens,
            preprocess=preprocess,
        )

        # Format the result with clear page markers
        if success:
            result = f"--- PAGE {page_index + 1} ---\n{result}\n"

        return success, result

    def process_multiple_images(
        self,
        image_paths: List[str],
        prompt: Optional[str] = None,
        maintain_context: bool = True,
        max_tokens: int = 8000,
        content_types: Optional[List[str]] = None,
        use_parallel: Optional[bool] = None,
        preprocess: Optional[bool] = None,
    ) -> Tuple[bool, Union[str, Dict]]:
        """
        Process multiple images with Claude's vision capabilities via CLI.

        Args:
            image_paths: List of paths to image files
            prompt: Custom prompt for Claude
            maintain_context: Whether to process images as a single context
            max_tokens: Maximum number of tokens for Claude's response
            content_types: Optional list of content types matching image_paths
                           If provided, must be same length as image_paths
            use_parallel: Whether to use parallel processing (defaults to class setting)
            preprocess: Whether to preprocess images (defaults to class setting)

        Returns:
            Tuple of (success, result)
        """
        # Verify all images exist
        for path in image_paths:
            if not os.path.exists(path):
                return False, f"Image file not found: {path}"

        # Check content_types if provided
        if content_types and len(content_types) != len(image_paths):
            return (
                False,
                "If content_types is provided, it must match length of image_paths",
            )

        # Determine whether to use parallel processing
        parallel_processing = (
            use_parallel
            if use_parallel is not None
            else self.enable_parallel_processing
        )

        # For backward compatibility, if prompt is provided, use the legacy approach
        if prompt is not None:
            # Default prompt for multiple images (backward compatibility)
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
                with tempfile.NamedTemporaryFile(
                    mode="w+", suffix=".txt", delete=False
                ) as temp_file:
                    result_path = temp_file.name

                    # Build command with multiple images
                    image_arguments = " ".join([f'"{path}"' for path in image_paths])
                    max_tokens_flag = f"--max-tokens {max_tokens}"
                    command = f'{self.claude_command} {self.model_flag} {max_tokens_flag} {image_arguments} "{prompt}" > {result_path}'

                    # Execute the command
                    result = subprocess.run(
                        command, shell=True, capture_output=True, text=True
                    )

                    if result.returncode != 0:
                        return False, f"Claude CLI failed: {result.stderr}"

                    # Read the result
                    with open(result_path, "r") as f:
                        claude_response = f.read()

                    # Delete temporary file
                    try:
                        os.unlink(result_path)
                    except Exception:
                        pass

                    return True, claude_response.strip()

            except Exception as e:
                self.logger.error(
                    f"Error processing multiple images with Claude CLI: {e}"
                )
                return False, f"Error processing images: {str(e)}"

        # Use new approach: sequential or parallel processing depending on context needs
        try:
            total_pages = len(image_paths)
            combined_result = ""
            processed_count = 0
            should_preprocess = (
                preprocess if preprocess is not None else self.enable_preprocessing
            )

            # If context matters, we need to process sequentially
            if maintain_context:
                self.logger.info(
                    f"Processing {total_pages} pages sequentially to maintain context"
                )

                # Process pages in sequential order
                current_context = ""  # Start with empty context

                for i, image_path in enumerate(image_paths):
                    # Get content type, either from provided list or auto-detect
                    page_content_type = (
                        content_types[i]
                        if content_types
                        else self.detect_content_type(image_path)
                    )

                    self.logger.info(
                        f"Processing page {i + 1}/{total_pages} (content type: {page_content_type})"
                    )

                    # Process with context from previous pages
                    success, page_result = self._process_single_image_for_batch(
                        image_path=image_path,
                        page_index=i,
                        total_pages=total_pages,
                        content_type=page_content_type,
                        context=current_context if i > 0 else None,
                        preprocess=should_preprocess,
                        max_tokens=max_tokens // 2,  # Leave room for context
                    )

                    if not success:
                        self.logger.error(
                            f"Failed to process page {i + 1}: {page_result}"
                        )
                        return False, f"Failed to process page {i + 1}: {page_result}"

                    # Update combined result
                    combined_result += page_result
                    processed_count += 1

                    # Update context with a summary/excerpt of previous content
                    # (limit to avoid exceeding token limits)
                    if (
                        i < total_pages - 1
                    ):  # No need to update context for the last page
                        # Take only the last portion as context for the next page
                        context_limit = 500  # Characters limit for context
                        current_context = (
                            combined_result[-context_limit:]
                            if len(combined_result) > context_limit
                            else combined_result
                        )

            # If context doesn't matter, we can process in parallel
            elif parallel_processing and total_pages > 1:
                self.logger.info(
                    f"Processing {total_pages} pages in parallel (max workers: {self.max_parallel_workers})"
                )

                # Define the worker function for parallel processing
                def process_page(args):
                    idx, img_path = args
                    # Get content type, either from provided list or auto-detect
                    page_ct = (
                        content_types[idx]
                        if content_types
                        else self.detect_content_type(img_path)
                    )
                    return self._process_single_image_for_batch(
                        image_path=img_path,
                        page_index=idx,
                        total_pages=total_pages,
                        content_type=page_ct,
                        preprocess=should_preprocess,
                        max_tokens=max_tokens,
                    )

                # Process pages in parallel
                page_results = []
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(self.max_parallel_workers, total_pages)
                ) as executor:
                    futures = {
                        executor.submit(process_page, (i, path)): i
                        for i, path in enumerate(image_paths)
                    }

                    for future in concurrent.futures.as_completed(futures):
                        page_index = futures[future]
                        try:
                            success, page_result = future.result()
                            if success:
                                page_results.append((page_index, page_result))
                                self.logger.info(
                                    f"Successfully processed page {page_index + 1}/{total_pages}"
                                )
                                processed_count += 1
                            else:
                                self.logger.error(
                                    f"Failed to process page {page_index + 1}: {page_result}"
                                )
                                # Continue processing other pages even if one fails
                        except Exception as e:
                            self.logger.error(
                                f"Error processing page {page_index + 1}: {e}"
                            )

                # Sort results by page index and combine
                page_results.sort(key=lambda x: x[0])  # Sort by page index
                combined_result = "\n".join([result for _, result in page_results])

            # Fallback to sequential processing without context
            else:
                self.logger.info(
                    f"Processing {total_pages} pages sequentially (parallel disabled)"
                )

                for i, image_path in enumerate(image_paths):
                    # Get content type, either from provided list or auto-detect
                    page_content_type = (
                        content_types[i]
                        if content_types
                        else self.detect_content_type(image_path)
                    )

                    self.logger.info(
                        f"Processing page {i + 1}/{total_pages} (content type: {page_content_type})"
                    )

                    # Process without context
                    success, page_result = self._process_single_image_for_batch(
                        image_path=image_path,
                        page_index=i,
                        total_pages=total_pages,
                        content_type=page_content_type,
                        preprocess=should_preprocess,
                        max_tokens=max_tokens,
                    )

                    if success:
                        combined_result += page_result
                        processed_count += 1
                    else:
                        self.logger.error(
                            f"Failed to process page {i + 1}: {page_result}"
                        )
                        # Continue processing other pages even if one fails

            # Check if we processed any pages successfully
            if processed_count == 0:
                return False, "Failed to process any pages"

            # Return success if we processed at least one page
            success_rate = processed_count / total_pages
            if success_rate < 1.0:
                self.logger.warning(
                    f"Partial success: processed {processed_count}/{total_pages} pages ({success_rate:.1%})"
                )

            return True, combined_result

        except Exception as e:
            self.logger.error(f"Error in multi-page processing: {e}")
            return False, f"Error in multi-page processing: {str(e)}"

    def safe_process_with_retries(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        content_type: str = "text",
        retries: int = 3,
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
        # random and time already imported at module level

        attempt = 0

        while attempt < retries:
            try:
                result = self.process_image(image_path, prompt, content_type)
                return result
            except Exception as e:
                # Retry with exponential backoff
                delay = (2**attempt) + random.uniform(0, 1)
                self.logger.warning(
                    f"Error, retrying in {delay:.2f} seconds (attempt {attempt + 1}/{retries}): {e}"
                )
                time.sleep(delay)
                attempt += 1

        return False, "Failed after multiple retry attempts"
