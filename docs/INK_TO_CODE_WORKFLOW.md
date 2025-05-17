# Ink-to-Code Workflow

This document describes the implementation of the Ink-to-Code workflow in InkLink, which enables converting handwritten pseudocode to executable code using Claude Vision for handwriting recognition and Claude Code for code generation.

## Overview

The Ink-to-Code workflow allows users to:
1. Write pseudocode or algorithm descriptions on their reMarkable tablet
2. Add the `#code` tag to trigger code generation
3. Automatically detect code patterns and programming language hints
4. Generate executable code using Claude Code
5. Receive formatted code responses with syntax highlighting back on their tablet

## Architecture

The workflow is implemented through several new services:

### 1. Code Recognition Service
- **File**: `src/inklink/services/code_recognition_service.py`
- **Purpose**: Detects code/pseudocode patterns in handwritten text
- **Features**:
  - Tag detection (`#code`, `#pseudocode`, `#algorithm`)
  - Automatic pattern recognition (functions, classes, control flow)
  - Programming language detection
  - Code block extraction and cleaning

### 2. Enhanced Handwriting Service
- **File**: `src/inklink/services/enhanced_handwriting_service.py`
- **Purpose**: Extends base handwriting recognition with code detection
- **Features**:
  - Integrated code detection during recognition
  - Automatic routing to appropriate services
  - Support for code-specific recognition settings
  - Tag-based action mapping

### 3. Ink-to-Code Service
- **File**: `src/inklink/services/ink_to_code_service.py`
- **Purpose**: Orchestrates the complete workflow
- **Features**:
  - End-to-end processing from handwriting to code
  - Integration with Claude Code via LLM Service Manager
  - Response formatting with optional syntax highlighting
  - Multi-page notebook processing

## Usage

### Basic Example

```python
from inklink.services.ink_to_code_service import InkToCodeService

# Initialize the service
ink_to_code = InkToCodeService()

# Process a handwritten code query
success, result = ink_to_code.process_code_query("/path/to/notebook.rm")

if success:
    print(f"Generated code: {result['generated_code']}")
    print(f"Uploaded to: {result['upload_message']}")
```

### Tag Usage

Users can trigger code generation by adding tags to their handwritten notes:

- `#code` - Generate executable code from pseudocode
- `#review` - Review existing code for improvements
- `#debug` - Debug code and suggest fixes
- `#explain` - Explain what the code does
- `#optimize` - Optimize code for performance
- `#test` - Generate unit tests

### Automatic Detection

The system can automatically detect code content without tags by recognizing patterns like:
- Function definitions
- Class declarations
- Control flow statements
- Variable declarations
- Algorithm descriptions

## Code Detection Patterns

The Code Recognition Service uses sophisticated pattern matching to identify:

1. **Function Patterns**: `def`, `function`, `func`, method signatures
2. **Class Patterns**: `class`, `struct`, `interface` declarations
3. **Control Flow**: `if`, `while`, `for`, `else`, `return`
4. **Variables**: Type declarations, assignments
5. **Algorithm Markers**: `algorithm`, `procedure`, `step N`
6. **Code Structure**: Braces, indentation, comments

## Language Detection

The system can detect hints for various programming languages:
- Python: `def`, `import`, `self`, `__init__`
- JavaScript: `function`, `const`, `=>`, `async`
- Java: `public`, `private`, `static`, `void`
- C++: `std::`, `cout`, `#include`
- Go: `func`, `package`, `defer`
- Rust: `fn`, `mut`, `impl`, `match`

## Response Formatting

Generated code responses include:
1. Original handwritten query
2. Generated code with syntax highlighting (if enabled)
3. Explanation of the code
4. Metadata (language, confidence, tags)

## Configuration

The workflow can be configured through environment variables:

```python
# Enable/disable code detection
INKLINK_CODE_DETECTION_ENABLED = True

# Enable/disable automatic routing
INKLINK_AUTO_ROUTING_ENABLED = True

# Enable/disable syntax highlighting
INKLINK_SYNTAX_HIGHLIGHTING = True

# Code generation tags
INKLINK_CODE_TAG = "code"
INKLINK_PSEUDOCODE_TAG = "pseudocode"
INKLINK_ALGORITHM_TAG = "algorithm"
```

## Example Workflows

### 1. Simple Function Generation

Write on reMarkable:
```
#code
function fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

Generated Python code:
```python
def fibonacci(n):
    """Calculate the nth Fibonacci number using recursion."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
```

### 2. Algorithm to Code

Write on reMarkable:
```
#algorithm #code
Binary Search:
1. Set left = 0, right = length - 1
2. While left <= right:
   - Calculate mid = (left + right) / 2
   - If array[mid] == target: return mid
   - If array[mid] < target: left = mid + 1
   - Else: right = mid - 1
3. Return -1 (not found)
```

Generated code:
```python
def binary_search(array, target):
    """Perform binary search on a sorted array."""
    left = 0
    right = len(array) - 1
    
    while left <= right:
        mid = (left + right) // 2
        
        if array[mid] == target:
            return mid
        elif array[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1
```

### 3. Code Review

Write on reMarkable:
```
#review
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[0]
    less = [x for x in arr[1:] if x <= pivot]
    greater = [x for x in arr[1:] if x > pivot]
    return quicksort(less) + [pivot] + quicksort(greater)
```

Response includes:
- Code analysis
- Suggestions for improvement
- Performance considerations
- Best practices

## Testing

Run the test suite:
```bash
# Test code recognition
python -m pytest tests/services/test_code_recognition.py

# Test ink-to-code service  
python -m pytest tests/services/test_ink_to_code.py

# Run the demo
python examples/ink_to_code_demo.py
```

## Future Enhancements

1. **Multi-language Support**: Expand language detection and generation
2. **Code Completion**: Partial code completion from snippets
3. **Refactoring Suggestions**: Automated refactoring recommendations
4. **Integration with IDEs**: Export to development environments
5. **Version Control**: Track code evolution across notebook versions
6. **Collaborative Coding**: Share code snippets with team members

## Troubleshooting

### Code Not Detected
- Ensure the `#code` tag is clearly written
- Check that code patterns are recognizable
- Verify handwriting is legible

### Wrong Language Generated
- Add language hints in comments or tags
- Use language-specific syntax in pseudocode
- Specify target language with tags like `#python` or `#javascript`

### Poor Code Quality
- Provide more detailed pseudocode
- Include type information and constraints
- Add comments about intended behavior

## Resources

- [Code Recognition Service](../src/inklink/services/code_recognition_service.py)
- [Enhanced Handwriting Service](../src/inklink/services/enhanced_handwriting_service.py)
- [Ink-to-Code Service](../src/inklink/services/ink_to_code_service.py)
- [Demo Script](../examples/ink_to_code_demo.py)
- [Test Suite](../tests/services/test_ink_to_code.py)