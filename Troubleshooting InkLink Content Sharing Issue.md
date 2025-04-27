# Troubleshooting InkLink Content Sharing Issue

# Diagnosing and Fixing InkLink's Blank Notebook Issue

Based on the drawj2d documentation, I can identify the likely cause of the blank notebook issue. InkLink is successfully creating notebooks on the reMarkable device, but they're empty because of issues in the conversion pipeline.

## Root Causes and Fix

The primary issues appear to be:

1. **Incorrect drawj2d parameters for your specific reMarkable model**
2. **HCL script formatting issues**
3. **Conversion command execution problems**

Let's implement a systematic fix:

### 1. First, determine which reMarkable model you have

Are you using a reMarkable 2 or a reMarkable Pro? This matters because:

- reMarkable 2: 157mm × 209mm (monochrome)
- reMarkable Pro: 179mm × 239mm (color support)

### 2. Update your document_service.py file

```python
def _convert_to_remarkable(self, hcl_path: str, rm_path: str) -> Optional[str]:
    """Convert HCL file to Remarkable format using drawj2d."""
    try:
        logger.info(f"Starting conversion from {hcl_path} to {rm_path}")

        # Input validation
        if not os.path.exists(hcl_path):
            error_msg = format_error("input", "HCL file not found", hcl_path)
            logger.error(error_msg)
            return None

        # Log HCL content for debugging
        with open(hcl_path, "r", encoding="utf-8") as f:
            hcl_content = f.read()
            logger.debug(f"HCL file content: {hcl_content}")

        # Check output path
        output_dir = os.path.dirname(rm_path)
        if not os.path.exists(output_dir):
            logger.info(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)

        # IMPORTANT: Modified command to match drawj2d documentation
        # For reMarkable 2, use -Trm (raw page data)
        cmd = [self.drawj2d_path, "-Trm", "-o", rm_path, hcl_path]
        logger.info(f"Conversion command: {' '.join(cmd)}")

        # Run the conversion
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        logger.debug(f"Command stdout: {result.stdout}")
        logger.debug(f"Command stderr: {result.stderr}")

        if result.returncode != 0:
            # Try alternate format for backward compatibility (without -rmv6)
            logger.warning("First conversion attempt failed, trying alternate format...")
            
            # Try -Trmdoc format instead (for direct USB or cloud upload)
            alt_rm_path = rm_path.replace('.rm', '.rmdoc')
            alt_cmd = [self.drawj2d_path, "-Trmdoc", "-o", alt_rm_path, hcl_path]
            logger.info(f"Alternate conversion command: {' '.join(alt_cmd)}")
            
            alt_result = subprocess.run(alt_cmd, capture_output=True, text=True, check=False)
            logger.debug(f"Alternate command stdout: {alt_result.stdout}")
            logger.debug(f"Alternate command stderr: {alt_result.stderr}")
            
            if alt_result.returncode == 0:
                logger.info(f"Alternate conversion successful: {alt_rm_path}")
                return alt_rm_path
            else:
                raise RuntimeError(f"All conversion attempts failed. First error: {result.stderr}, Second error: {alt_result.stderr}")

        # Verify the output file exists and has content
        if not os.path.exists(rm_path):
            logger.error(f"Output file missing: {rm_path}")
            return None
            
        file_size = os.path.getsize(rm_path)
        logger.info(f"Output file created: {rm_path} ({file_size} bytes)")
        
        if file_size < 50:
            logger.error(f"Output file too small: {file_size} bytes")
            return None
            
        # Read and log binary file header for debugging
        with open(rm_path, "rb") as rf:
            header = rf.read(100)
            logger.debug(f"RM file header (hex): {header.hex()}")
            
        return rm_path
        
    except Exception as e:
        logger.error(format_error("conversion", "Failed to convert document", e))
        return None
```

### 3. Fix HCL generation

Update your `create_hcl` method in document_service.py:

```python
def create_hcl(self, url: str, qr_path: str, content: Dict[str, Any]) -> Optional[str]:
    """Create HCL script from web content."""
    try:
        # Ensure we have valid content, even if minimal
        if not content:
            content = {"title": f"Page from {url}", "structured_content": []}

        logger.info(f"Creating HCL document for: {content.get('title', url)}")

        # Generate HCL file path
        hcl_filename = f"doc_{hash(url)}_{int(time.time())}.hcl"
        hcl_path = os.path.join(self.temp_dir, hcl_filename)

        with open(hcl_path, "w", encoding="utf-8") as f:
            # Use specific font for reMarkable
            f.write('font Lines\n')
            
            # Set page size - use exact dimensions for device
            # reMarkable 2: 1404 x 1872 (in drawj2d internal units, physical = 157mm x 209mm)
            # reMarkable Pro: 1404 x 1872 (adjust for your model if needed)
            f.write('size 1404 1872\n')

            # Set pen color to black 
            f.write('pen black\n\n')

            # Starting position
            y_pos = 100
            
            # Add title
            title = content.get("title", "Untitled Document")
            f.write(f'moveto 100 {y_pos}\n')
            f.write(f'font bold 6\n')
            f.write(f'text {{"{self._escape_hcl(title)}"}}\n')
            
            # Space after title
            y_pos += 40
            
            # Add URL under title
            f.write(f'moveto 100 {y_pos}\n')
            f.write('font plain 4\n')
            f.write(f'text {{Source: {self._escape_hcl(url)}}}\n')
            y_pos += 40

            # Add horizontal line separator 
            f.write(f'moveto 100 {y_pos}\n')
            f.write(f'line 100 {y_pos} 1300 {y_pos} width=1.0\n')
            y_pos += 40

            # Add QR code if available
            if os.path.exists(qr_path):
                f.write(f'moveto 1000 {y_pos}\n')
                f.write(f'image {qr_path}\n')

            # Process structured content
            y_pos += 50

            # Process content items
            for item in content.get("structured_content", []):
                item_type = item.get("type", "paragraph")
                item_content = item.get("content", "")
                
                if not item_content:
                    continue
                
                if y_pos > 1800:  # Check for page overflow
                    f.write('newpage\n')
                    y_pos = 100
                
                # Handle different content types
                if item_type in ["h1", "heading"]:
                    f.write(f'moveto 100 {y_pos}\n')
                    f.write('font bold 5\n')
                    f.write(f'text {{"{self._escape_hcl(item_content)}"}}\n')
                    f.write('font plain 4\n')
                    y_pos += 50
                elif item_type == "paragraph":
                    f.write(f'moveto 100 {y_pos}\n')
                    f.write(f'text {{"{self._escape_hcl(item_content)}"}}\n')
                    y_pos += 40
                # Add more type handlers as needed
            
            # Add timestamp
            f.write(f'moveto 100 1800\n')
            f.write('font plain 3\n')
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f'text {{Generated: {timestamp}}}\n')

        logger.info(f"Created HCL file: {hcl_path}")
        # Debug - log the content
        with open(hcl_path, "r", encoding="utf-8") as f:
            logger.debug(f"HCL content: {f.read()}")

        return hcl_path
    except Exception as e:
        logger.error(f"Error creating HCL document: {e}")
        return None
```

## Testing Steps

1. Update the code as shown above
2. Check the exact version of drawj2d you have installed:

```other
docker exec -it inklink /usr/bin/drawj2d --version
```

3. Create a simple test HCL file to verify basic functionality:

```other
font Lines
size 1404 1872
pen black
moveto 400 400
text {Test content - does this appear?}
```

4. Try manual conversion to verify drawj2d is working:

```other
docker exec -it inklink /usr/bin/drawj2d -Trm -o /tmp/test.rm /tmp/test.hcl
```

5. Upload the test file manually to verify rmapi is working:

```other
docker exec -it inklink /usr/local/bin/rmapi put /tmp/test.rm /
```

## Additional Diagnostics

If it still doesn't work after these changes, enable DEBUG logging to see exactly what's happening:

```other
docker-compose down
INKLINK_LOG_LEVEL=DEBUG docker-compose up -d
```

Then test again and check the logs:

```other
docker-compose logs -f
```

---

### Additional Information:

# Fixing InkLink for reMarkable Pro and reMarkable 2

Based on the documentation you've shared and knowing you primarily use a reMarkable Pro with occasional use of reMarkable 2, I can provide a targeted solution. The key issue is that drawj2d needs specific parameters for each device model, and the HCL script generation needs to be correct.

## Core Changes Needed

### 1. Update the HCL Generation for reMarkable Pro

The most important change is to correctly set the page dimensions and format for reMarkable Pro:

```python
def create_hcl(self, url: str, qr_path: str, content: Dict[str, Any]) -> Optional[str]:
    """Create HCL script from web content."""
    try:
        # Device detection (can be set via config)
        is_remarkable_pro = True  # Set this based on configuration or preference
        
        # Ensure we have valid content
        if not content:
            content = {"title": f"Page from {url}", "structured_content": []}

        logger.info(f"Creating HCL document for: {content.get('title', url)}")

        # Generate HCL file path
        hcl_filename = f"doc_{hash(url)}_{int(time.time())}.hcl"
        hcl_path = os.path.join(self.temp_dir, hcl_filename)

        with open(hcl_path, "w", encoding="utf-8") as f:
            # Use Lines font for proper display on reMarkable
            f.write('font Lines\n')
            
            # Set correct page dimensions - critical for content to display
            if is_remarkable_pro:
                # reMarkable Pro: 179mm × 239mm
                f.write('size 1700 2200\n')  # Adjusted for Pro dimensions
            else:
                # reMarkable 2: 157mm × 209mm
                f.write('size 1404 1872\n')
            
            # Set pen color to black for visibility
            f.write('pen black\n\n')

            # Starting position
            y_pos = 120
            
            # Add title with proper formatting
            title = content.get("title", "Untitled Document")
            f.write(f'moveto 120 {y_pos}\n')
            f.write(f'font bold 6\n')
            f.write(f'text {{"{self._escape_hcl(title)}"}}\n')
            
            # Continue with content...
```

### 2. Fix the Conversion Command in document_service.py

```python
def _convert_to_remarkable(self, hcl_path: str, rm_path: str) -> Optional[str]:
    """Convert HCL file to Remarkable format using drawj2d."""
    try:
        # For reMarkable Pro (primary device)
        is_remarkable_pro = True  # Set based on configuration
        
        if is_remarkable_pro:
            # For Pro: use Trmdoc format
            cmd = [self.drawj2d_path, "-Trmdoc", "-o", rm_path, hcl_path]
        else:
            # For reMarkable 2: use Trm format
            cmd = [self.drawj2d_path, "-Trm", "-o", rm_path, hcl_path]
        
        logger.info(f"Conversion command: {' '.join(cmd)}")
        
        # Execute command
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        logger.info(f"Command stdout: {result.stdout}")
        logger.info(f"Command stderr: {result.stderr}")
        
        # Verify output exists with proper size
        if not os.path.exists(rm_path):
            logger.error(f"Output file missing: {rm_path}")
            return None
        
        file_size = os.path.getsize(rm_path)
        logger.info(f"Output file created: {rm_path} ({file_size} bytes)")
        
        return rm_path
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        return None
```

## Verification Steps

1. Create a simple test file to verify drawj2d works correctly:

```other
# SSH into your Docker container
docker exec -it inklink bash

# Create a simple test HCL file
cat > /tmp/test.hcl << 'EOF'
font Lines
size 1700 2200
pen black
moveto 400 400
text {Test content for reMarkable Pro}
EOF

# Test conversion for Pro model
/usr/bin/drawj2d -Trmdoc -o /tmp/test.rmdoc /tmp/test.hcl

# Test uploading to reMarkable
/usr/local/bin/rmapi put /tmp/test.rmdoc /
```

2. Verify the correct drawj2d parameters:

Unlike my previous suggestion that had both `-Trm` and `-rmv6` flags, the documentation shows we should use:

- `-Trm` for reMarkable 2 (produces .rm file)
- `-Trmdoc` for reMarkable Pro (produces .rmdoc file)
- `-Trmn` for notebook format (for RCU upload)

## Configuration Option

Add a configuration option to specify your primary device:

```python
# In config.py
CONFIG = {
    # ... existing configuration
    "REMARKABLE_MODEL": os.environ.get("INKLINK_RM_MODEL", "pro"),  # "pro" or "rm2"
}
```

Then use this in your document service:

```python
is_remarkable_pro = CONFIG.get("REMARKABLE_MODEL", "pro").lower() == "pro"
```

## Integration with RemarkableService

Update your RemarkableService to handle the appropriate file format:

```python
def upload(self, doc_path: str, title: str) -> Tuple[bool, str]:
    """Upload document to Remarkable Cloud"""
    try:
        # Validate inputs
        if not os.path.exists(doc_path):
            error_msg = format_error("input", "Document not found", doc_path)
            logger.error(error_msg)
            return False, error_msg

        # If rmapi is not available, report error
        if not os.path.exists(self.rmapi_path):
            error_msg = f"rmapi executable not found at {self.rmapi_path}"
            logger.error(error_msg)
            return False, error_msg

        # Use the upload method with retries
        sanitized_title = self._sanitize_filename(title)
        
        # Check file extension to determine upload command
        if doc_path.endswith('.rmdoc'):
            # For rmdoc files (reMarkable Pro)
            success, message = self._upload_rmdoc(doc_path, sanitized_title)
        else:
            # For rm files (reMarkable 2)
            success, message = self._upload_with_n_flag(doc_path, sanitized_title)
            
        # Rest of function...
```

## Complete Testing Plan

1. Add debug logs to all key functions
2. Test with a simple URL first
3. Verify the generated HCL file has correct content
4. Verify the conversion command executes successfully
5. Check the output file size and format
6. Check the upload command and confirm success
7. Verify the notebook appears on your reMarkable device

?descriptionFromFileType=function+toLocaleUpperCase()+{+[native+code]+}+File&mimeType=application/octet-stream&fileName=Troubleshooting+InkLink+Content+Sharing+Issue.md&fileType=undefined&fileExtension=md