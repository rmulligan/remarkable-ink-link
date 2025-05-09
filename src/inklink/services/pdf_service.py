"""PDF processing service for Pi Share Receiver."""

import os
import requests
import PyPDF2
from urllib.parse import urlparse
from typing import Dict, Optional, Any
import logging
import pdf2image
import graphviz
import reportlab
import reportlab.lib.pagesizes
import reportlab.pdfgen
import reportlab.pdfgen.canvas
import reportlab.platypus
import reportlab.lib.colors
import reportlab.lib.styles

# Configure logging
logger = logging.getLogger(__name__)


class PDFService:
    """Handles PDF processing operations."""

    def __init__(self, temp_dir: str, extract_dir: str):
        """Initialize with directories for temporary and extracted files.

        Args:
            temp_dir: Directory for temporary PDF storage
            extract_dir: Directory for PDF content extraction
        """
        self.temp_dir = temp_dir
        self.extract_dir = extract_dir
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(extract_dir, exist_ok=True)

    def is_pdf_url(self, url: str) -> bool:
        """Check if URL points to a PDF file.

        Args:
            url: URL to check

        Returns:
            True if URL is PDF, False otherwise
        """
        # Simple extension check
        if url.lower().endswith(".pdf"):
            return True

        # Check content type from headers
        try:
            headers = requests.head(url, allow_redirects=True, timeout=10).headers
            content_type = headers.get("Content-Type", "").lower()
            return "application/pdf" in content_type
        except Exception as e:
            logger.error(f"Error checking if URL is PDF: {e}")
            return False

    def process_pdf(self, url: str, qr_path: str) -> Optional[Dict[str, Any]]:
        """Download and process PDF from URL.

        Args:
            url: The PDF URL to download
            qr_path: Path to QR code image

        Returns:
            Dict containing PDF info or None if failed
        """
        try:
            logger.info(f"Processing PDF URL: {url}")

            # Create filename for PDF
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename or not filename.lower().endswith(".pdf"):
                filename = f"document_{hash(url)}.pdf"

            pdf_path = os.path.join(self.temp_dir, filename)

            # Download PDF
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(pdf_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Extract title from PDF metadata or filename
            title = self._extract_pdf_title(pdf_path, url)

            mode = "outline"
            if mode == "raster":
                from pdf2image import convert_from_path

                images = convert_from_path(pdf_path)
                image_paths = []
                base, _ = os.path.splitext(filename)
                for i, img in enumerate(images, start=1):
                    img_name = f"{base}_page_{i}.png"
                    img_path = os.path.join(self.temp_dir, img_name)
                    img.save(img_path, "PNG")
                    image_paths.append(img_path)
                # Include original PDF path in result for consistency
                return {"title": title, "images": image_paths, "pdf_path": pdf_path}

            return {"title": title, "pdf_path": pdf_path}

        except Exception as e:
            logger.error(f"Error processing PDF URL: {e}")
            return None

    def _extract_pdf_title(self, pdf_path: str, url: str) -> str:
        """Extract title from PDF metadata or create from URL.

        Args:
            pdf_path: Path to downloaded PDF file
            url: Original URL

        Returns:
            Title string
        """
        try:
            # Try to get title from PDF metadata
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                if reader.metadata and reader.metadata.title:
                    return reader.metadata.title

            # Fall back to filename from URL
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if filename.lower().endswith(".pdf"):
                filename = filename[:-4]  # Remove .pdf extension

            # Format filename as title
            title = filename.replace("_", " ").replace("-", " ")
            return title or "PDF Document"

        except Exception as e:
            logger.error(f"Error extracting PDF title: {e}")
            return "PDF Document"

    def generate_index_notebook(
        self, pages: list, output_path: str, graph_title: str = "Index Node Graph"
    ) -> None:
        """
        Generate an index notebook as a PDF containing a node graph with cross-references.

        Args:
            pages: List of dicts, each with keys:
                - 'title': Title of the handwritten page
                - 'summary': Short summary of the page
                - 'page_number': Page number in the notebook
                - 'device_location': Device-specific location or identifier
                - 'links': List of page numbers this page references (optional)
            output_path: Path to save the generated PDF
            graph_title: Title for the node graph

        Returns:
            None. Writes the PDF to output_path.

        The node graph is generated using Graphviz and embedded in the PDF.
        Each node represents a page, with edges for cross-references.
        The PDF includes a table of pages with titles, summaries, page numbers, and device locations.
        """
        import tempfile
        from graphviz import Digraph
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.platypus import (
            Table,
            TableStyle,
            SimpleDocTemplate,
            Paragraph,
            Spacer,
        )
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        import os

        # Step 1: Build the node graph using Graphviz
        graphviz_obj = Digraph(comment=graph_title)
        for page in pages:
            label = f"{page['page_number']}: {page['title']}"
            graphviz_obj.node(str(page["page_number"]), label)
        for page in pages:
            if "links" in page:
                for ref in page["links"]:
                    graphviz_obj.edge(str(page["page_number"]), str(ref))

        # Step 2: Render the graph to a temporary PNG file
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_path = os.path.join(tmpdir, "index_graph.png")
            graphviz_obj.render(filename=graph_path, format="png", cleanup=True)
            graph_img_path = graph_path + ".png"

            # Step 3: Build the PDF
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            elements.append(Paragraph(graph_title, styles["Title"]))
            elements.append(Spacer(1, 12))

            # Insert the node graph image
            from reportlab.platypus import Image

            elements.append(Image(graph_img_path, width=500, height=300))
            elements.append(Spacer(1, 24))

            # Table of pages
            data = [["Page", "Title", "Summary", "Device Location"]]
            for page in pages:
                data.append(
                    [
                        page["page_number"],
                        page["title"],
                        page.get("summary", ""),
                        page.get("device_location", ""),
                    ]
                )
            table = Table(data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            elements.append(table)
            elements.append(Spacer(1, 24))

            # Add cross-reference details
            elements.append(Paragraph("Cross-References", styles["Heading2"]))
            for page in pages:
                if "links" in page and page["links"]:
                    refs = ", ".join(str(ref) for ref in page["links"])
                    elements.append(
                        Paragraph(
                            f"Page {page['page_number']} references: {refs}",
                            styles["Normal"],
                        )
                    )

            doc.build(elements)
