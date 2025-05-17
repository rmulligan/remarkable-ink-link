# Claude Code and MyScript Migration Context

This document explains the current handwriting recognition architecture in InkLink and how Claude Code integration relates to the MyScript implementation.

## Current Architecture

InkLink currently has a flexible handwriting recognition system with multiple backends:

### 1. Primary: Claude Vision
- **Service**: `handwriting_recognition_service.py` 
- **Adapter**: `claude_vision_adapter.py`
- **Configuration**: `HANDWRITING_BACKEND: "claude_vision"`
- **Features**:
  - Direct image-to-text recognition
  - Content classification (text/math/diagram)
  - Tag processing
  - Knowledge graph integration

### 2. Secondary: Ollama Vision
- **Service**: Same service, different adapter
- **Adapter**: `ollama_vision_adapter.py`
- **Configuration**: `HANDWRITING_BACKEND: "ollama_vision"`
- **Features**:
  - Local model support
  - Privacy-focused processing
  - Similar capabilities to Claude Vision

### 3. Legacy: MyScript Web API
- **Service**: Could be integrated as another backend
- **Adapter**: `handwriting_web_adapter.py`
- **Configuration**: `HANDWRITING_BACKEND: "myscript"` (not currently implemented)
- **Features**:
  - Stroke-based recognition
  - Mathematical expression support
  - Multi-language support
  - API-based recognition

## Current Backend Selection

The system uses an "auto" mode by default, which selects backends based on:
1. Availability (is the service accessible?)
2. Performance (which gives better results?)
3. Privacy settings (local vs cloud)

```python
# From config.py
"HANDWRITING_BACKEND": os.environ.get("HANDWRITING_BACKEND", "auto")
```

## MyScript Implementation Status

### What Exists:
1. **HandwritingWebAdapter**: Complete implementation for MyScript Web API
   - Authentication with API keys
   - Stroke data formatting
   - Recognition requests
   - Result parsing

2. **HandwritingAdapter**: Legacy SDK adapter (incomplete)
   - Intended for local MyScript SDK
   - Not actively used

3. **Documentation**: Complete setup and usage guides
   - API configuration
   - Testing procedures
   - Troubleshooting

### What's Missing:
1. Integration into the service layer's backend selection
2. Configuration in the main handwriting service
3. Fallback logic when Claude Vision is unavailable

## Claude Code Integration Context

Claude Code is **NOT** a replacement for handwriting recognition. Instead:

### Primary Purpose:
- Code generation from handwritten pseudocode
- Code review and debugging
- Technical documentation
- Software development assistance

### Relationship to Handwriting:
1. **Depends on**: Handwriting recognition to extract text from notebooks
2. **Processes**: The extracted text to generate/review code
3. **Complements**: Vision models by adding code-specific intelligence

## Migration Path for MyScript

To fully integrate MyScript as a handwriting backend:

### 1. Service Layer Integration
```python
# In handwriting_recognition_service.py
def __init__(self, backend="auto", ...):
    if backend == "myscript":
        self.adapter = HandwritingWebAdapter(...)
    elif backend == "claude_vision":
        self.adapter = ClaudeVisionAdapter(...)
    # etc.
```

### 2. Configuration Update
```python
# In config.py
"MYSCRIPT_APP_KEY": os.environ.get("MYSCRIPT_APP_KEY"),
"MYSCRIPT_HMAC_KEY": os.environ.get("MYSCRIPT_HMAC_KEY"),
```

### 3. Backend Selection Logic
```python
# Auto-select based on availability and config
if self.backend == "auto":
    if claude_vision_available():
        use_claude_vision()
    elif myscript_configured():
        use_myscript()
    elif ollama_available():
        use_ollama()
```

### 4. Unified Interface
All backends should implement the same interface:
- `recognize_handwriting(image_path, content_type, language)`
- `classify_region(image_path)`
- `ping()` for availability checks

## Claude Code's Role

Claude Code enhances the system by:

1. **Post-Processing**: Taking recognized text and generating code
2. **Intelligence Layer**: Understanding code intent from natural language
3. **Integration**: Working with all handwriting backends equally

## Benefits of Multiple Backends

1. **Redundancy**: Fallback options when primary service is unavailable
2. **Performance**: Choose best backend for specific content types
3. **Privacy**: Local options for sensitive content
4. **Cost**: Balance between API costs and accuracy needs

## Recommended Architecture

```
User Input (Handwritten) 
    ↓
Handwriting Recognition Layer
    ├── Claude Vision (primary)
    ├── MyScript (mathematical)
    └── Ollama (local/private)
    ↓
Text Extraction
    ↓
Content Processing Layer
    ├── Claude Code (for code)
    ├── Claude (for general)
    └── Local LLMs (for private)
    ↓
Output Generation
```

## Next Steps

1. **Complete MyScript Integration**:
   - Add to backend selection in service
   - Test with mathematical expressions
   - Create fallback logic

2. **Enhance Claude Code**:
   - Add specific handling for code detection
   - Integrate with knowledge graph
   - Create code-specific workflows

3. **Unified Testing**:
   - Test all backend combinations
   - Performance benchmarks
   - Accuracy comparisons

## Conclusion

MyScript and Claude Code serve different purposes:
- MyScript: Handwriting → Text (recognition layer)
- Claude Code: Text → Code (intelligence layer)

Both are valuable components that work together to create a comprehensive system for processing handwritten technical content.