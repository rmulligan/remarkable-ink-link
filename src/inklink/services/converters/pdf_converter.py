"""PDF content converter for InkLink.

This module provides a converter that transforms PDF files
into reMarkable-compatible formats.
"""

import os
import subprocess
import logging
from typing import Dict, Any, Optional, List

from inklink.services.converters.base_converter import BaseConverter
from inklink.config import CONFIG

logger = logging.getLogger(__name__)


class PDFConverter(BaseConverter):
    """Converts PDF files to reMarkable format."""
    
    def can_convert(self, content_type: str) -> bool:
        """Check if this converter can handle the given content type."""
        return content_type == "pdf"
    
    def convert(self, content: Dict[str, Any], output_path: Optional[str] = None) -> Optional[str]:
        """
        Convert PDF file to reMarkable format.
        
        Args:
            content: Dictionary containing content and metadata
                    Should include:
                    - pdf_path: Path to the PDF file
                    - title: Content title
                    - qr_path: Optional path to QR code image
                    - images: Optional list of image paths for multi-page PDFs
            output_path: Optional explicit output path
            
        Returns:
            Path to generated .rm file or None if failed
        """
        try:
            pdf_path = content.get("pdf_path", "")
            title = content.get("title", os.path.basename(pdf_path))
            qr_path = content.get("qr_path", "")
            images = content.get("images", [])
            use_rcu = content.get("use_rcu", True)
            
            if not pdf_path or not os.path.exists(pdf_path):
                logger.error(f"PDF file not found: {pdf_path}")
                return None
            
            if not use_rcu:
                # Convert using legacy HCL method
                return self._convert_pdf_legacy(pdf_path, title, qr_path, images)
            
            # Generate output path if not provided
            if not output_path:
                output_path = self._generate_temp_path("pdf", pdf_path, "rm")
            
            # Use RCU to convert PDF to reMarkable format
            cmd = [
                "rcu",
                "convert",
                "--input",
                pdf_path,
                "--output",
                output_path,
                "--title",
                title,
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Successfully converted PDF to reMarkable format: {output_path}")
                return output_path
            else:
                logger.error(f"PDF conversion failed: {result.stderr}")
                # Try falling back to legacy method
                return self._convert_pdf_legacy(pdf_path, title, qr_path, images)
                
        except Exception as e:
            logger.error(f"Error converting PDF: {str(e)}")
            return None
            
    def _convert_pdf_legacy(self, pdf_path: str, title: str, qr_path: Optional[str] = None,
                           images: Optional[List[str]] = None) -> Optional[str]:
        """
        Convert PDF file to reMarkable format using HCL and drawj2d.
        
        Args:
            pdf_path: Path to the PDF file
            title: Content title
            qr_path: Optional path to QR code image
            images: Optional list of image paths for multi-page PDFs
            
        Returns:
            Path to generated .rm file or None if failed
        """
        try:
            # Generate HCL file
            hcl_path = self._create_pdf_hcl(pdf_path, title, qr_path, images)
            if not hcl_path:
                logger.error("Failed to create HCL script for PDF")
                return None
            
            # Generate output path
            rm_path = self._generate_temp_path("rm", pdf_path, "rm")
            
            # Check if drawj2d_path is available
            drawj2d_path = CONFIG.get("DRAWJ2D_PATH")
            if not drawj2d_path or not os.path.exists(drawj2d_path):
                logger.error("drawj2d path not available for legacy conversion")
                return None
            
            # Run drawj2d
            cmd = [drawj2d_path, "-Trm", "-rmv6", "-o", rm_path, hcl_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0 and os.path.exists(rm_path):
                logger.info(f"Legacy PDF conversion successful: {rm_path}")
                return rm_path
            else:
                logger.error(f"Legacy PDF conversion failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error in legacy PDF conversion: {str(e)}")
            return None
            
    def _create_pdf_hcl(self, pdf_path: str, title: str, qr_path: Optional[str] = None,
                       images: Optional[List[str]] = None) -> Optional[str]:
        """
        Create HCL script for PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            title: Content title
            qr_path: Optional path to QR code image
            images: Optional list of image paths for multi-page PDFs
            
        Returns:
            Path to generated HCL file or None if failed
        """
        try:
            logger.info(f"Creating HCL document for PDF: {pdf_path}")
            
            # Generate HCL file path
            hcl_path = self._generate_temp_path("pdf", pdf_path, "hcl")
            
            with open(hcl_path, "w", encoding="utf-8") as f:
                # Set page size
                f.write(f'puts "size {self.page_width} {self.page_height}"\n\n')
                
                # Set font and pen
                f.write(f'puts "set_font {self.heading_font} 36"\n')
                f.write('puts "pen black"\n\n')
                
                # Set title position
                y_pos = self.margin
                
                # Add title
                f.write(f'puts "text {self.margin} {y_pos} \\"{self._escape_hcl(title)}\\""\n')
                y_pos += self.line_height * 1.5
                
                # Add PDF source under title
                f.write(f'puts "set_font {self.body_font} 20"\n')
                f.write(f'puts "text {self.margin} {y_pos} \\"Source: {self._escape_hcl(os.path.basename(pdf_path))}\\""\n')
                y_pos += self.line_height
                
                # Add horizontal line separator
                f.write(f'puts "line {self.margin} {y_pos} {self.page_width - self.margin} {y_pos} width=1.0"\n')
                y_pos += self.line_height * 2
                
                # Add QR code if available
                if qr_path and os.path.exists(qr_path):
                    qr_size = 350
                    qr_x = self.page_width - self.margin - qr_size
                    f.write(f'puts "rectangle {qr_x - 5} {y_pos - 5} {qr_size + 10} {qr_size + 10} width=1.0"\n')
                    f.write(f'puts "image {qr_x} {y_pos} {qr_size} {qr_size} \\"{qr_path}\\""\n')
                    y_pos += qr_size + self.line_height
                
                # Embed PDF vector outlines if in outline mode and no raster images
                # drawj2d will interpret PDF and redraw vector data as editable strokes
                mode = CONFIG.get("PDF_RENDER_MODE", "outline")
                if not images and mode == "outline":
                    # Use configured page and scale
                    page = CONFIG.get("PDF_PAGE", 1)
                    scale = CONFIG.get("PDF_SCALE", 1.0)
                    # Position at left margin
                    f.write(f'puts "moveto {self.margin} 0"\n')
                    # Embed specified PDF page at given scale
                    f.write(f'puts "image {pdf_path} {page} 0 0 {scale}"\n')
                # Embed raster images if provided
                elif images:
                    for img_path in images:
                        f.write('puts "newpage"\n')
                        # We would normally use PIL's Image here, but to avoid additional dependencies
                        # we'll estimate the image size
                        max_w = self.page_width - 2 * self.margin
                        x = self.margin
                        y = self.margin
                        f.write(f'puts "image {x} {y} {max_w} {self.page_height - 2 * self.margin} \\"{img_path}\\""\n')
                else:
                    # Add instructions for viewing the PDF
                    f.write(f'puts "text {self.margin} {y_pos} \\"This document has been converted to Remarkable format.\\""\n')
                    y_pos += self.line_height
                    f.write(f'puts "text {self.margin} {y_pos} \\"Original PDF: {self._escape_hcl(os.path.basename(pdf_path))}\\""\n')
                
                # Add timestamp at the bottom of the page
                timestamp = self._get_timestamp()
                f.write(f'puts "text {self.margin} {self.page_height - self.margin} \\"Generated: {timestamp}\\""\n')
            
            logger.info(f"Created HCL file for PDF: {hcl_path}")
            return hcl_path
            
        except Exception as e:
            logger.error(f"Error creating HCL document for PDF: {str(e)}")
            return None