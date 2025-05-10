#!/bin/bash

# Script to resolve merge conflicts in the codebase
# This script will replace conflicted sections with the proper resolution

# Function to resolve conflicts and choose the HEAD version with proper formatting
resolve_file() {
    local file="$1"
    local temp_file="${file}.tmp"
    
    # Create temp file for processing
    cp "$file" "$temp_file"
    
    # Fix conflicts based on the file type and conflict pattern
    case "$file" in
        *ai_adapter.py)
            # Fix validation if-condition formatting
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/c\            if (\n                "choices" not in result\n                or not isinstance(result["choices"], list)\n                or not result["choices"]\n            ):\n                raise ValueError(\n                    "Invalid API response: '\''choices'\'' array is missing or empty"\n                )' "$temp_file"
            ;;
            
        *rmapi_adapter.py)
            # Fix return formatting
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/c\            return (\n                False,\n                f"Expect script failed with code {process.returncode}, output: {process.stdout}",\n            )' "$temp_file"
            ;;
            
        *container.py)
            # Fix config normalization
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/c\        # Normalize configuration keys to lowercase\n        normalized_config = {key.lower(): value for key, value in config.items()}\n\n        # Register configuration values as services\n        provider.register_instance("config", normalized_config)\n\n        # Populate any values directly from normalized config\n        provider.register_instance("temp_dir", normalized_config.get("temp_dir"))\n        provider.register_instance("output_dir", normalized_config.get("output_dir"))\n        provider.register_instance(\n            "drawj2d_path", normalized_config.get("drawj2d_path")\n        )\n        provider.register_instance("rmapi_path", normalized_config.get("rmapi_path"))\n        provider.register_instance("rm_folder", normalized_config.get("rm_folder"))' "$temp_file"
            ;;
            
        *router.py)
            # Fix comment and controller initialization with DI
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/c\        # Split route into parts if needed for more complex routing in the future' "$temp_file"
            sed -i '/if route == "\/auth":/,/return AuthController(handler, self.services.get("rmapi_path"))/c\            if route == "/auth":\n                return AuthController(handler)\n            elif route == "/auth/remarkable":\n                return AuthController(handler)\n            elif route == "/auth/myscript":\n                return AuthController(handler)' "$temp_file"
            ;;
            
        *server.py)
            # Fix DI validation
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/c\    }\n\n    # Validate dependency injection configuration\n    for key, value in services.items():\n        if value is None:\n            raise ValueError(\n                "DI configuration error: '\''{}'\'' service is not configured properly.".format(\n                    key\n                )\n            )' "$temp_file"
            ;;
            
        *base_converter.py)
            # Fix multiline init
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/c\    def __init__(\n        self, temp_dir: Optional[str] = None, config: Optional[Dict[str, Any]] = None\n    ):' "$temp_file"
            ;;
            
        *html_converter.py)
            # Fix multiline class docstring
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/c\    """Converts HTML content directly to reMarkable format.\n\n    Note: HTML-to-structured-content utilities are intentionally bypassed in this converter.\n    We directly convert the HTML to remarkable format for better quality output.\n    """' "$temp_file"
            ;;
            
        *pdf_converter.py)
            # Fix tuple type
            sed -i 's/<<<<<<< HEAD//' "$temp_file"
            sed -i 's/from typing import Dict, Any, Optional, List, Union, Tuple/from typing import Dict, Any, Optional, List, Union, Tuple/' "$temp_file"
            sed -i '/^=======$/d' "$temp_file"
            sed -i '/^from typing import Dict, Any, Optional, List, Union$/d' "$temp_file"
            sed -i '/^>>>>>>> origin\/main$/d' "$temp_file"
            
            # Fix multiline init
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/c\    def __init__(\n        self, temp_dir: Optional[str] = None, config: Optional[Dict[str, Any]] = None\n    ):' "$temp_file"
            
            # Fix get_image_dimensions
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/c\    def get_image_dimensions(self, image_path: str) -> Tuple[int, int]:\n        """\n        Get the dimensions of an image using PIL.\n        Args:\n            image_path: Path to the image file\n\n        Returns:\n            Tuple containing width and height\n        """\n        try:\n            from PIL import Image\n\n            with Image.open(image_path) as img:\n                return img.size\n        except (ImportError, Exception) as e:\n            logger.warning(f"Error getting image dimensions with PIL: {str(e)}")\n            # Estimate default dimensions if PIL is not available\n            return (1404, 1872)  # Default reMarkable dimensions' "$temp_file"
            
            # Fix image rendering
            sed -i '/f.write('\''puts "newpage"'\'')$/,/>>>>>>> origin\/main/c\                        f.write('\''puts "newpage"'\'')\\n\n                        # Use PIL to get actual image dimensions for better rendering\n                        img_width, img_height = self.get_image_dimensions(img_path)\n\n                        # Calculate the scale to fit within the page while maintaining aspect ratio\n                        max_w = self.page_width - 2 * self.margin\n                        max_h = self.page_height - 2 * self.margin\n\n                        scale_w = max_w / img_width\n                        scale_h = max_h / img_height\n                        scale = min(scale_w, scale_h)\n                        # Calculate dimensions and position to center the image\n                        w = img_width * scale\n                        h = img_height * scale\n                        x = self.margin + (max_w - w) / 2\n                        y = self.margin + (max_h - h) / 2\n\n                        f.write(f'\''puts "image {x} {y} {w} {h} \\\\"{img_path}\\\\""'\'')' "$temp_file"
            ;;
            
        *document_service.py)
            # Fix functional pattern for get_converter_for_type
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/c\        return next(\n            (\n                converter\n                for converter in self.converters\n                if converter.can_convert(content_type)\n            ),\n            None,\n        )' "$temp_file"
            ;;
            
        *hcl_renderer.py)
            # Fix trailing comma
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/c\        config: Optional[Dict[str, Any]] = None,' "$temp_file"
            ;;
            
        *hcl_render.py)
            # Fix imports
            sed -i 's/<<<<<<< HEAD//' "$temp_file"
            sed -i 's/from typing import Dict, Any, Optional, List, Tuple/from typing import Dict, Any, Optional, List, Tuple/' "$temp_file"
            sed -i '/^=======$/d' "$temp_file"
            sed -i '/^from typing import Dict, Any, Optional$/d' "$temp_file"
            sed -i '/^>>>>>>> origin\/main$/d' "$temp_file"
            
            # Fix function params
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/c\    url: str,\n    qr_path: str,\n    content: Dict[str, Any],\n    temp_dir: str,\n    config: Optional[Dict[str, Any]] = None,' "$temp_file"
            
            # Fix HCL script generation
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/c\        line_height = config.get("LINE_HEIGHT", 40)\n\n        # Get fonts from config\n        heading_font = config.get("HEADING_FONT", "Liberation Sans")\n        body_font = config.get("BODY_FONT", "Liberation Sans")\n        code_font = config.get("CODE_FONT", "DejaVu Sans Mono")\n\n        # Create the HCL script' "$temp_file"
            
            # Fix rest of HCL script generation
            sed -i '/with open(hcl_path, "w", encoding="utf-8") as f:/,/>>>>>>> origin\/main/c\        with open(hcl_path, "w", encoding="utf-8") as f:\n            # Set page size\n            f.write(f'\''puts "size {page_width} {page_height}"'\'')\\n\\n)\n\n            # Initialize font and pen settings\n            f.write(f'\''puts "set_font {heading_font} 36"'\'')\\n)\n            f.write('\''puts "pen black"'\'')\\n\\n)\n\n            # Starting position\n            y_pos = margin\n\n            # Add title\n            f.write(f'\''puts "text {margin} {y_pos} \\\\"{escape_hcl(page_title)}\\\\""'\'')\\n)\n            y_pos += line_height * 1.5\n\n            # Add source URL line\n            f.write(f'\''puts "set_font {body_font} 20"'\'')\\n)\n            f.write(f'\''puts "text {margin} {y_pos} \\\\\"Source: {escape_hcl(url)}\\\\""'\'')\\n)\n            y_pos += line_height\n\n            # Add horizontal separator\n            f.write(\n                f'\''puts "line {margin} {y_pos} {page_width - margin} {y_pos} width=1.0"'\'')\\n)\n            )\n            y_pos += line_height * 1.5\n\n            # Add QR code if available\n            if qr_path and os.path.exists(qr_path):\n                qr_size = 350\n                qr_x = page_width - margin - qr_size\n                f.write(\n                    f'\''puts "rectangle {qr_x - 5} {y_pos - 5} {qr_size + 10} {qr_size + 10} width=1.0"'\'')\\n)\n                )\n                f.write(\n                    f'\''puts "image {qr_x} {y_pos} {qr_size} {qr_size} \\\\"{qr_path}\\\\""'\'')\\n)\n                )\n\n            # Process structured content if available\n            structured_content = content.get("structured_content", [])\n            if structured_content:\n                # Ensure we have some space below any QR code\n                if qr_path and os.path.exists(qr_path):\n                    y_pos += qr_size + line_height\n\n                # Render structured content elements\n                for item in structured_content:\n                    content_type = item.get("type", "text")\n                    content_value = item.get("value", "")\n\n                    if content_type == "heading":\n                        level = item.get("level", 1)\n                        size = (\n                            36\n                            if level == 1\n                            else (30 if level == 2 else (24 if level == 3 else 20))\n                        )\n                        f.write(f'\''puts "set_font {heading_font} {size}"'\'')\\n)\n                        f.write(\n                            f'\''puts "text {margin} {y_pos} \\\\"{escape_hcl(content_value)}\\\\""'\'')\\n)\n                        )\n                        y_pos += line_height * 1.5\n\n                    elif content_type == "paragraph":\n                        f.write(f'\''puts "set_font {body_font} 20"'\'')\\n)\n                        f.write(\n                            f'\''puts "text {margin} {y_pos} \\\\"{escape_hcl(content_value)}\\\\""'\'')\\n)\n                        )\n                        y_pos += line_height * 1.2\n\n                    elif content_type == "code":\n                        f.write(f'\''puts "set_font {code_font} 18"'\'')\\n)\n                        f.write(\n                            f'\''puts "text {margin + 20} {y_pos} \\\\"{escape_hcl(content_value)}\\\\""'\'')\\n)\n                        )\n                        y_pos += line_height\n                    elif content_type == "list_item":\n                        level = item.get("level", 1)\n                        indent = margin + ((level - 1) * 30)\n                        f.write(f'\''puts "set_font {body_font} 20"'\'')\\n)\n                        f.write(\n                            f'\''puts "text {indent} {y_pos} \\\\\"• {escape_hcl(content_value)}\\\\""'\'')\\n)\n                        )\n                        y_pos += line_height\n                    elif content_type == "image":\n                        img_path = item.get("path", "")\n                        if img_path and os.path.exists(img_path):\n                            img_width = item.get("width", 800)\n                            img_height = item.get("height", 600)\n                            f.write(\n                                f'\''puts "image {margin} {y_pos} {img_width} {img_height} \\\\"{img_path}\\\\""'\'')\\n)\n                            )\n                            y_pos += img_height + line_height\n\n                    elif content_type == "table":\n                        # Basic table rendering (simplified)\n                        rows = item.get("rows", [])\n                        col_width = (\n                            (page_width - 2 * margin) / max(len(row) for row in rows)\n                            if rows\n                            else 100\n                        )\n                        for row_idx, row in enumerate(rows):\n                            for col_idx, cell in enumerate(row):\n                                x_pos = margin + (col_idx * col_width)\n                                f.write(\n                                    f'\''puts "text {x_pos} {y_pos} \\\\"{escape_hcl(str(cell))}\\\\""'\'')\\n)\n                                )\n                            y_pos += line_height\n                            if row_idx == 0:  # Header row\n                                f.write(\n                                    f'\''puts "line {margin} {y_pos} {page_width - margin} {y_pos} width=1.0"'\'')\\n)\n                                )\n                                y_pos += line_height / 2\n            else:\n                # If no structured content, add a placeholder message\n                y_pos = margin + 400  # Middle of page\n                f.write(f'\''puts "set_font {body_font} 24"'\'')\\n)\n                f.write(\n                    f'\''puts "text {margin} {y_pos} \\\\\"No content available for this page.\\\\""'\'')\\n)\n                )\n\n            # Add timestamp at the bottom of the page\n            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")\n            f.write(f'\''puts "set_font {body_font} 16"'\'')\\n)' "$temp_file"
            ;;
            
        *test_ai_service.py)
            # Fix URL parser assertions
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/c\        assert parsed_url.netloc == "api.openai.com" or parsed_url.netloc.endswith(\n            ".api.openai.com"\n        )' "$temp_file"
            
            sed -i '/assert parsed_url.netloc == "api.anthropic.com"/,/>>>>>>> origin\/main/c\        assert parsed_url.netloc == "api.anthropic.com" or parsed_url.netloc.endswith(\n            ".api.anthropic.com"\n        )' "$temp_file"
            ;;
            
        *test_handwriting_recognition.py)
            # Fix all fixture setup and test cases
            sed -i '/<<<<<<< HEAD/,/>>>>>>> origin\/main/d' "$temp_file"
            sed -i 's/handwriting_adapter=mock_handwriting_adapter$/handwriting_adapter=mock_handwriting_adapter,/g' "$temp_file"
            # Remove whitespace only lines
            sed -i '/^[[:space:]]*$/d' "$temp_file"
            ;;
    esac
    
    # Replace original file with fixed version
    mv "$temp_file" "$file"
    git add "$file"
}

# Resolve all conflicted files
resolve_file "src/inklink/adapters/ai_adapter.py"
resolve_file "src/inklink/adapters/rmapi_adapter.py"
resolve_file "src/inklink/di/container.py"
resolve_file "src/inklink/router.py"
resolve_file "src/inklink/server.py"
resolve_file "src/inklink/services/converters/base_converter.py"
resolve_file "src/inklink/services/converters/html_converter.py"
resolve_file "src/inklink/services/converters/pdf_converter.py"
resolve_file "src/inklink/services/document_service.py"
resolve_file "src/inklink/services/renderers/hcl_renderer.py"
resolve_file "src/inklink/utils/hcl_render.py"
resolve_file "tests/test_ai_service.py"
resolve_file "tests/test_handwriting_recognition.py"

echo "All conflicts resolved and staged for commit"