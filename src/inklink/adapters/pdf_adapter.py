"""PDF adapter for InkLink.

This module provides an adapter for PDF processing operations.
"""

import os
import logging
import tempfile
from typing import Dict, Any, Optional, List, Tuple, BinaryIO, Union
import PyPDF2
from pdf2image import convert_from_path

from inklink.adapters.adapter import Adapter

logger = logging.getLogger(__name__)


class PDFAdapter(Adapter):
    """Adapter for PDF processing operations using PyPDF2 and pdf2image."""
    
    def __init__(self, temp_dir: str):
        """
        Initialize with temporary directory for PDF operations.
        
        Args:
            temp_dir: Directory for temporary files
        """
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
    
    def ping(self) -> bool:
        """
        Check if PDF processing libraries are available.
        
        Returns:
            True if all required libraries are available, False otherwise
        """
        try:
            # Check PyPDF2
            PyPDF2.PdfReader
            
            # Check pdf2image (will throw ImportError if not installed)
            convert_from_path
            
            # Check if temp directory is writable
            with tempfile.NamedTemporaryFile(dir=self.temp_dir, delete=True) as tmp:
                tmp.write(b"test")
                
            return True
        except (ImportError, PermissionError, IOError) as e:
            logger.error(f"PDF adapter check failed: {e}")
            return False
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary of metadata
        """
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                
                metadata = {}
                
                if reader.metadata:
                    # Extract standard metadata fields
                    for field in ['title', 'author', 'subject', 'creator', 'producer']:
                        value = getattr(reader.metadata, field, None)
                        if value:
                            metadata[field] = value
                
                # Add page count
                metadata['page_count'] = len(reader.pages)
                
                # Extract first page text as sample
                if len(reader.pages) > 0:
                    try:
                        metadata['first_page_sample'] = reader.pages[0].extract_text()[:500]
                    except Exception as e:
                        logger.warning(f"Could not extract sample text: {e}")
                
                return metadata
                
        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {e}")
            return {"error": str(e)}
    
    def extract_title(self, pdf_path: str, default_title: str = "PDF Document") -> str:
        """
        Extract title from PDF metadata or return default.
        
        Args:
            pdf_path: Path to PDF file
            default_title: Default title to use if extraction fails
            
        Returns:
            Title string
        """
        try:
            metadata = self.extract_metadata(pdf_path)
            if 'title' in metadata and metadata['title']:
                return metadata['title']
            
            # Fall back to filename without extension
            filename = os.path.basename(pdf_path)
            if filename.lower().endswith('.pdf'):
                name_only = filename[:-4]  # Remove .pdf extension
                formatted_name = name_only.replace('_', ' ').replace('-', ' ').strip()
                if formatted_name:
                    return formatted_name
            
            return default_title
            
        except Exception as e:
            logger.error(f"Error extracting PDF title: {e}")
            return default_title
    
    def convert_to_images(self, 
                       pdf_path: str,
                       output_dir: Optional[str] = None,
                       dpi: int = 300,
                       fmt: str = 'PNG') -> List[str]:
        """
        Convert PDF to images.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save images (defaults to temp_dir)
            dpi: Image DPI
            fmt: Image format ('PNG', 'JPEG', etc.)
            
        Returns:
            List of paths to generated images
        """
        try:
            save_dir = output_dir or self.temp_dir
            os.makedirs(save_dir, exist_ok=True)
            
            # Convert PDF pages to images
            images = convert_from_path(pdf_path, dpi=dpi)
            
            image_paths = []
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            
            # Save each image
            for i, img in enumerate(images, start=1):
                img_path = os.path.join(save_dir, f"{base_name}_page_{i}.{fmt.lower()}")
                img.save(img_path, fmt)
                image_paths.append(img_path)
            
            return image_paths
            
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            return []
    
    def merge_pdfs(self, pdf_paths: List[str], output_path: str) -> bool:
        """
        Merge multiple PDFs into a single PDF.
        
        Args:
            pdf_paths: List of PDF file paths to merge
            output_path: Path for the merged PDF
            
        Returns:
            True if successful, False otherwise
        """
        try:
            merger = PyPDF2.PdfMerger()
            
            for pdf in pdf_paths:
                merger.append(pdf)
            
            merger.write(output_path)
            merger.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error merging PDFs: {e}")
            return False
    
    def split_pdf(self, pdf_path: str, output_dir: str) -> List[str]:
        """
        Split a PDF into separate pages.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save split pages
            
        Returns:
            List of paths to individual PDF pages
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                page_count = len(reader.pages)
                
                # Create output filenames
                base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                output_files = []
                
                # Extract and save each page
                for page_num in range(page_count):
                    output_file = os.path.join(output_dir, f"{base_name}_page_{page_num+1}.pdf")
                    writer = PyPDF2.PdfWriter()
                    writer.add_page(reader.pages[page_num])
                    
                    with open(output_file, 'wb') as output:
                        writer.write(output)
                    
                    output_files.append(output_file)
                
                return output_files
                
        except Exception as e:
            logger.error(f"Error splitting PDF: {e}")
            return []
    
    def extract_text(self, pdf_path: str) -> List[str]:
        """
        Extract text from each page of a PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of extracted text strings, one per page
        """
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text_pages = []
                
                for page in reader.pages:
                    text = page.extract_text()
                    text_pages.append(text)
                
                return text_pages
                
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return []
    
    def add_watermark(self, 
                   pdf_path: str, 
                   watermark_path: str, 
                   output_path: str) -> bool:
        """
        Add watermark (like a QR code) to each page of a PDF.
        
        Args:
            pdf_path: Path to PDF file
            watermark_path: Path to watermark PDF
            output_path: Path to save watermarked PDF
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Open the original PDF
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                writer = PyPDF2.PdfWriter()
                
                # Open watermark PDF
                with open(watermark_path, 'rb') as watermark_file:
                    watermark = PyPDF2.PdfReader(watermark_file)
                    watermark_page = watermark.pages[0]
                    
                    # Apply watermark to each page
                    for page_num in range(len(reader.pages)):
                        page = reader.pages[page_num]
                        page.merge_page(watermark_page)
                        writer.add_page(page)
                
                # Save the watermarked PDF
                with open(output_path, 'wb') as output:
                    writer.write(output)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding watermark to PDF: {e}")
            return False
    
    def generate_graph_pdf(self, 
                        nodes: List[Dict[str, Any]], 
                        edges: List[Tuple[str, str]], 
                        output_path: str,
                        title: str = "Graph",
                        include_table: bool = True) -> bool:
        """
        Generate a PDF with a node graph and optional table.
        
        Args:
            nodes: List of node dictionaries, each with 'id' and 'label' keys
            edges: List of (source_id, target_id) tuples
            output_path: Path to save the PDF
            title: Title for the PDF
            include_table: Whether to include a table of nodes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import tempfile
            from graphviz import Digraph
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.platypus import (
                Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer, Image
            )
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet
            
            # Build graph using Graphviz
            graph = Digraph(comment=title)
            
            # Add nodes
            for node in nodes:
                node_id = str(node['id'])
                label = node.get('label', node_id)
                graph.node(node_id, label)
            
            # Add edges
            for source, target in edges:
                graph.edge(str(source), str(target))
            
            # Create PDF with reportlab
            with tempfile.TemporaryDirectory() as tmpdir:
                # Render graph to image
                graph_path = os.path.join(tmpdir, "graph")
                graph.render(filename=graph_path, format="png", cleanup=True)
                graph_img_path = graph_path + ".png"
                
                # Build PDF
                doc = SimpleDocTemplate(output_path, pagesize=letter)
                elements = []
                styles = getSampleStyleSheet()
                
                # Add title
                elements.append(Paragraph(title, styles["Title"]))
                elements.append(Spacer(1, 12))
                
                # Add graph image
                elements.append(Image(graph_img_path, width=500, height=300))
                elements.append(Spacer(1, 24))
                
                # Add table if requested
                if include_table and nodes:
                    # Create header row based on first node's keys
                    header_keys = [k for k in nodes[0].keys() if k != 'id']
                    header_keys.insert(0, 'id')  # Ensure ID is first column
                    
                    # Create table data
                    data = [header_keys]  # Header row
                    for node in nodes:
                        row = [str(node.get(k, '')) for k in header_keys]
                        data.append(row)
                    
                    # Create and style table
                    table = Table(data, repeatRows=1)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ]))
                    elements.append(table)
                
                # Build the PDF
                doc.build(elements)
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating graph PDF: {e}")
            return False