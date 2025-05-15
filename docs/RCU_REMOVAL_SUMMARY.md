# RCU Removal Summary

## Overview
This document summarizes the changes made to remove the RCU (reMarkable Content Uploader) dependency from the InkLink project. The RCU tool was previously used as a primary option for converting files to reMarkable format, with drawj2d as a fallback. Since RCU is a paid software ($12), we have refactored the code to use only the open-source drawj2d tool.

## Changes Made

### Removed Files
- `/src/inklink/utils/rcu.py` - Deleted the entire RCU utility module

### Updated Files
1. `/src/inklink/utils/common.py`:
   - Removed `ensure_rcu_available()` and added `ensure_drawj2d_available()` instead
   - Removed RCU-based conversion functions and implemented drawj2d alternatives
   - Added `create_hcl_from_markdown()` to support markdown conversion
   - Updated `convert_markdown_to_rm()` and `convert_html_to_rm()` to use drawj2d

2. `/src/inklink/utils/__init__.py`:
   - Updated imports and exports to use drawj2d functions instead of RCU functions
   - Added `create_hcl_from_markdown` to the exported functions

3. `/src/inklink/services/document_service.py`:
   - Changed imports from `ensure_rcu_available` to `ensure_drawj2d_available`
   - Updated initialization to check for drawj2d availability
   - Replaced `use_rcu` with `use_drawj2d` in all content processing
   - Updated error messages to reference drawj2d instead of RCU

4. `/src/inklink/services/converters/pdf_converter.py`:
   - Simplified PDF conversion to use drawj2d by default
   - Removed RCU-based conversion code

5. `/src/inklink/services/converters/markdown_converter.py`:
   - Updated code to use drawj2d for markdown conversion
   - Changed variable names from `use_rcu` to `use_drawj2d`

### Technical Details

#### HTML Conversion
For HTML conversion, we've implemented a two-step approach:
1. First try to convert HTML to markdown using html2text library
2. If that fails, extract text using a simple regex approach
3. Create an HCL file from the markdown/text
4. Use drawj2d to convert the HCL file to reMarkable format

#### Markdown Conversion
For markdown conversion:
1. Create an HCL file from markdown
2. Use drawj2d to convert the HCL file to reMarkable format

#### PDF Conversion
For PDF conversion:
1. Create an HCL file containing PDF content/references
2. Use drawj2d to render the HCL file to reMarkable format

## Testing
All conversion paths should be tested to verify functionality:
1. Markdown to reMarkable conversion
2. HTML to reMarkable conversion
3. PDF to reMarkable conversion
4. Structured content to reMarkable conversion

## Future Improvements
1. Enhance the HCL generation from markdown to better support formatting
2. Improve HTML-to-markdown conversion for better quality
3. Consider adding more robust PDF parsing and conversion