# Cleanup Plan for reMarkable-Ink-Link Codebase

## Overview
The codebase currently contains references to RCU (reMarkable Content Uploader), which is a paid software ($12) that we want to remove. We'll replace its functionality with the already available drawj2d tool which is currently used as a fallback.

## Analysis of Current Implementation
RCU is currently used for:
1. Converting Markdown files to reMarkable format
2. Converting HTML files to reMarkable format 
3. Converting PDF files to reMarkable format

The code already has a fallback mechanism that uses drawj2d when RCU is not available.

## Files to Modify

### 1. Remove RCU Utility Module
- `/home/ryan/dev/remarkable-ink-link/src/inklink/utils/rcu.py` - Delete this entire file

### 2. Update Import References
- `/home/ryan/dev/remarkable-ink-link/src/inklink/utils/__init__.py` - Remove RCU imports and exports
- `/home/ryan/dev/remarkable-ink-link/src/inklink/services/document_service.py` - Remove RCU imports

### 3. Update Common Utilities
- `/home/ryan/dev/remarkable-ink-link/src/inklink/utils/common.py` - Remove RCU-related functions and replace with drawj2d alternatives

### 4. Update Service Implementations
- `/home/ryan/dev/remarkable-ink-link/src/inklink/services/document_service.py` - Remove RCU checks and make drawj2d the default
- `/home/ryan/dev/remarkable-ink-link/src/inklink/services/converters/pdf_converter.py` - Update to use drawj2d by default
- `/home/ryan/dev/remarkable-ink-link/src/inklink/services/converters/markdown_converter.py` - Update to use drawj2d by default

### 5. Update Configuration
- `/home/ryan/dev/remarkable-ink-link/src/inklink/config.py` - Remove RCU references

## Implementation Plan

### 1. First, create a drawj2d utility function in common.py
Create a replacement for `ensure_rcu_available` that checks for drawj2d instead.

### 2. Update converters to use drawj2d by default
Modify the converters to use drawj2d without the RCU fallback logic.

### 3. Clean up RCU-specific imports and references
Remove the RCU-specific imports, exports, and utility functions.

### 4. Remove the RCU module
Delete the RCU utility module once all references are removed.

### 5. Verify the changes
Test the system to ensure that document conversion still works correctly with drawj2d.