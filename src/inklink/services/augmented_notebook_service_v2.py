"""Enhanced version of AugmentedNotebookService with syntax highlighting support."""

import logging
import re
from typing import Optional, Tuple, Dict, Any

from inklink.services.augmented_notebook_service import AugmentedNotebookService

logger = logging.getLogger(__name__)


class AugmentedNotebookServiceV2(AugmentedNotebookService):
    """
    Enhanced augmented notebook service with syntax highlighting for code blocks.

    This service extends the base service to detect code blocks in recognized
    text and render them with syntax highlighting when generating responses.
    """

    def _append_response_to_notebook(
        self,
        rm_file_path: str,
        response: str,
        include_sources: Optional[list] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Append Claude's response to the notebook with syntax highlighting support.

        Args:
            rm_file_path: Path to the original .rm file
            response: Claude's response text
            include_sources: Optional list of sources to include

        Returns:
            Tuple of (success, result dictionary)
        """
        try:
            # Check if response contains code blocks
            code_blocks = self._extract_code_blocks(response)

            if code_blocks:
                # We have code blocks - create a mixed document
                return self._create_mixed_response_document(
                    response, code_blocks, include_sources
                )
            else:
                # No code blocks - use the original method
                return super()._append_response_to_notebook(
                    rm_file_path, response, include_sources
                )

        except Exception as e:
            logger.error(f"Error appending response with syntax highlighting: {e}")
            return False, {"error": f"Failed to append response: {str(e)}"}

    def _extract_code_blocks(self, text: str) -> list:
        """
        Extract code blocks from markdown text.

        Args:
            text: Text potentially containing code blocks

        Returns:
            List of code block dictionaries with content and language
        """
        code_blocks = []

        # Pattern for fenced code blocks with optional language
        pattern = r"```(\w*)\n(.*?)\n```"

        matches = re.finditer(pattern, text, re.DOTALL)
        for match in matches:
            language = match.group(1) or "text"
            code = match.group(2)

            code_blocks.append(
                {
                    "language": language,
                    "code": code,
                    "start": match.start(),
                    "end": match.end(),
                    "full_match": match.group(0),
                }
            )

        # Also check for inline code (single backticks) if we want to highlight those
        # inline_pattern = r'`([^`]+)`'
        # inline_matches = re.finditer(inline_pattern, text)
        # for match in inline_matches:
        #     code_blocks.append({
        #         'language': 'text',
        #         'code': match.group(1),
        #         'start': match.start(),
        #         'end': match.end(),
        #         'inline': True
        #     })

        return code_blocks

    def _create_mixed_response_document(
        self,
        response: str,
        code_blocks: list,
        include_sources: Optional[list] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a document with mixed regular text and syntax-highlighted code.

        This is a simplified version - in production, we might want to:
        1. Create multiple .rm files and merge them
        2. Use a more sophisticated approach to mix editable ink and highlighted code
        3. Handle page breaks between text and code sections

        Args:
            response: Full response text
            code_blocks: List of extracted code blocks
            include_sources: Optional sources to include

        Returns:
            Tuple of (success, result dictionary)
        """
        try:
            # For now, create separate documents for each code block
            # In a full implementation, we'd want to merge these intelligently
            documents = []

            # Process each code block
            for i, block in enumerate(code_blocks):
                # Generate a title for the code block
                title = f"Code Block {i + 1} ({block['language']})"

                # Create syntax-highlighted document
                rm_path = self.document_service.create_syntax_highlighted_document(
                    code=block["code"],
                    language=block["language"],
                    title=title,
                    show_line_numbers=True,
                    show_metadata=True,
                )

                if rm_path:
                    documents.append(
                        {
                            "path": rm_path,
                            "type": "code",
                            "language": block["language"],
                            "position": block["start"],
                        }
                    )

            # Create the main text document with code blocks replaced by references
            modified_response = response
            for i, block in enumerate(code_blocks):
                replacement = f"\n[Code Block {i + 1}: See separate page]\n"
                modified_response = modified_response.replace(
                    block["full_match"], replacement
                )

            # Create main text document
            main_rm_path = self.document_service.create_editable_ink_document(
                text=modified_response,
                title="Response with Code Blocks",
            )

            if main_rm_path:
                documents.insert(
                    0, {"path": main_rm_path, "type": "text", "position": 0}
                )

            # Upload all documents
            # In a real implementation, we'd want to combine these into a single notebook
            upload_results = []
            for doc in documents:
                title = f"Response Part {documents.index(doc) + 1}"
                success, message = self.remarkable_service.upload(doc["path"], title)
                upload_results.append(
                    {"success": success, "message": message, "type": doc["type"]}
                )

            return True, {
                "documents": documents,
                "upload_results": upload_results,
                "code_blocks_count": len(code_blocks),
            }

        except Exception as e:
            logger.error(f"Error creating mixed response document: {e}")
            return False, {"error": f"Failed to create mixed document: {str(e)}"}
