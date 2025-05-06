from typing import Any, Dict, List, Optional
from .interfaces import IHandwritingRecognitionService
import logging

class RmsceneAdapter:
    """
    Adapter for rmscene tool to extract stroke data from ink files.
    This class should be replaced or mocked in tests.
    """
    def extract_strokes(self, ink_data: bytes = None, file_path: str = None) -> List[Dict[str, Any]]:
        try:
            # Placeholder: Replace with actual rmscene invocation logic
            # For example, call a subprocess or library to parse the file or bytes
            if file_path:
                # Simulate reading and extracting strokes from file
                return [{"x": [0, 1], "y": [0, 1]}]
            elif ink_data:
                # Simulate reading and extracting strokes from bytes
                return [{"x": [0, 1], "y": [0, 1]}]
            else:
                raise ValueError("No ink data or file path provided to rmscene adapter.")
        except Exception as e:
            logging.error(f"Rmscene extraction failed: {e}")
            raise

class MyScriptAdapter:
    """
    Adapter for MyScript SDK/API to perform handwriting recognition.
    This class should be replaced or mocked in tests.
    """
    def __init__(self):
        self.initialized = False

    def initialize(self, application_key: str, hmac_key: str) -> bool:
        # Placeholder: Replace with actual MyScript SDK initialization
        self.initialized = True
        return True

    def recognize(self, iink_data: Dict[str, Any], content_type: str = "Text", language: str = "en_US") -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("MyScript SDK not initialized.")
        # Placeholder: Replace with actual MyScript recognition logic
        return {"text": "recognized text", "structured": {"lines": ["recognized text"]}}

    def export(self, content_id: str, format_type: str = "text") -> Dict[str, Any]:
        # Placeholder: Replace with actual export logic
        return {"content_id": content_id, "format": format_type, "data": "exported content"}

class HandwritingRecognitionService(IHandwritingRecognitionService):
    """
    Service that wraps rmscene and MyScript for handwriting recognition.
    """
    def __init__(
        self,
        rmscene_adapter: Optional[RmsceneAdapter] = None,
        myscript_adapter: Optional[MyScriptAdapter] = None
    ):
        self.rmscene = rmscene_adapter or RmsceneAdapter()
        self.myscript = myscript_adapter or MyScriptAdapter()

    def classify_region(self, strokes: List[Dict[str, Any]]) -> str:
        """
        Classify a region as 'text', 'math', or 'diagram' based on stroke features.
        Placeholder: Uses simple heuristics (to be replaced with ML or SDK logic).
        """
        # Example heuristic: very basic, for demonstration
        if len(strokes) > 0:
            # If many strokes and some are long, guess diagram
            if any(len(s["x"]) > 10 for s in strokes):
                return "Diagram"
            # If strokes are dense and short, guess math
            if len(strokes) > 5:
                return "Math"
        return "Text"

    def initialize_iink_sdk(self, application_key: str, hmac_key: str) -> bool:
        try:
            return self.myscript.initialize(application_key, hmac_key)
        except Exception as e:
            logging.error(f"MyScript SDK initialization failed: {e}")
            return False

    def extract_strokes(self, rm_file_path: str) -> List[Dict[str, Any]]:
        try:
            return self.rmscene.extract_strokes(file_path=rm_file_path)
        except Exception as e:
            logging.error(f"Stroke extraction failed: {e}")
            return []

    def convert_to_iink_format(self, strokes: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            # Placeholder: Convert strokes to MyScript/iink format
            # This should be replaced with actual conversion logic
            return {"strokes": strokes}
        except Exception as e:
            logging.error(f"Conversion to iink format failed: {e}")
            return {}

    def recognize_handwriting(
        self,
        iink_data: Dict[str, Any],
        content_type: str = "Text",
        language: str = "en_US"
    ) -> Dict[str, Any]:
        try:
            return self.myscript.recognize(iink_data, content_type, language)
        except Exception as e:
            logging.error(f"Handwriting recognition failed: {e}")
            return {"error": str(e)}

    def export_content(self, content_id: str, format_type: str = "text") -> Dict[str, Any]:
        try:
            return self.myscript.export(content_id, format_type)
        except Exception as e:
            logging.error(f"Export failed: {e}")
            return {"error": str(e)}

    def recognize_from_ink(
        self,
        ink_data: bytes = None,
        file_path: str = None,
        content_type: str = None,
        language: str = "en_US"
    ) -> Dict[str, Any]:
        """
        High-level method: Accepts ink data or file path, extracts strokes, classifies region, recognizes handwriting, and returns result.
        If content_type is None or 'auto', classify region automatically.
        """
        try:
            strokes = self.rmscene.extract_strokes(ink_data=ink_data, file_path=file_path)
            if content_type is None or content_type.lower() == "auto":
                content_type = self.classify_region(strokes)
            iink_data = self.convert_to_iink_format(strokes)
            result = self.myscript.recognize(iink_data, content_type, language)
            return result
        except Exception as e:
            logging.error(f"Handwriting recognition pipeline failed: {e}")
    def recognize_multi_page_ink(
        self,
        page_files: List[str],
        language: str = "en_US",
        user_links: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Recognize handwriting from multiple page files, maintaining per-page and cross-page context.

        Args:
            page_files (List[str]): List of file paths, each representing a handwritten page.
            language (str): Language code for recognition.
            user_links (Optional[List[Dict[str, Any]]]): Optional user-defined cross-page links, e.g.,
                [{"from_page": 1, "to_page": 2, "type": "reference", "label": "See Figure 1"}]

        Returns:
            Dict[str, Any]: Structured content with per-page items and cross-page links.
                {
                    "pages": [...],
                    "cross_page_links": [...]
                }
        """
        structured_pages = []
        cross_page_links = user_links[:] if user_links else []

        # Temporary storage for automatic cross-page references
        reference_map = {}

        for i, file_path in enumerate(page_files):
            strokes = self.rmscene.extract_strokes(file_path=file_path)
            content_type = self.classify_region(strokes)
            iink_data = self.convert_to_iink_format(strokes)
            result = self.myscript.recognize(iink_data, content_type, language)

            items = []
            page_references = []

            # Example: extract recognized items and look for references
            if "text" in result:
                text = result["text"]
                items.append({"type": content_type.lower(), "content": text})

                # Simple automatic cross-page reference extraction (e.g., "see page X")
                import re
                ref_matches = re.findall(r"(see|refer to) page (\d+)", text, re.IGNORECASE)
                for _, ref_page in ref_matches:
                    ref_page_num = int(ref_page)
                    if 1 <= ref_page_num <= len(page_files) and ref_page_num != (i + 1):
                        link = {
                            "from_page": i + 1,
                            "to_page": ref_page_num,
                            "type": "auto_reference",
                            "label": f"Reference to page {ref_page_num}",
                        }
                        cross_page_links.append(link)
                        page_references.append(link)

            structured_pages.append({
                "page_number": i + 1,
                "items": items,
                "metadata": {
                    "references": page_references
                }
            })

        # Remove duplicate links (by from_page, to_page, type, label)
        seen = set()
        unique_links = []
        for link in cross_page_links:
            key = (link["from_page"], link["to_page"], link.get("type"), link.get("label"))
            if key not in seen:
                unique_links.append(link)
                seen.add(key)

        return {
            "pages": structured_pages,
            "cross_page_links": unique_links
        }