# Repository Organization Plan

This document outlines the plan for cleaning up and organizing the reMarkable Ink Link repository.

## 1. Directory Structure Cleanup

### Core Directories to Keep
- `src/` - Main source code
- `tests/` - Test suite
- `docs/` - Documentation
- `scripts/` - Utility scripts
- `web/` - Web UI components

### Directories to Clean or Reorganize
- `temp/`, `temp_extract/`, `temp_files/`, `temp_container/` - Consolidate or remove temporary files
- `handwriting_model/` - Organize model files and remove redundant test data
- `downloaded_notebooks/`, `downloads/` - Add to gitignore and maintain clean structure

## 2. Documentation Organization

Reorganize documentation into a structured hierarchy:
```
/docs
├── README.md                     # Overview of documentation
├── user/                         # User guides
├── developer/                    # Developer documentation
├── integrations/                 # Integration-specific documentation
│   ├── remarkable/               # reMarkable integration
│   ├── claude-vision/            # Claude vision capabilities
│   ├── limitless/                # Limitless integration
│   └── knowledge-graph/          # Knowledge Graph integration
├── guides/                       # Workflow guides
└── reports/                      # Test reports and status info
```

### Documentation Consolidation
- Remove legacy MyScript documentation as it's no longer used
- Create new documentation for Claude vision integration
- Standardize Limitless integration docs
- Create template for new integration documentation

## 3. Source Code Organization

### Code Structure Improvements
- Consolidate utility functions from `utils.py` into appropriate modules in `utils/` directory
- Group related services into subdirectories by domain (recognition, document, knowledge)
- Update adapters to reflect the new Claude vision-based approach
- Refactor the router implementation for better maintainability

### Code Cleanup
- Remove MyScript-related code that is no longer needed
- Remove backup files (*.bak)
- Fix inconsistent implementations
- Standardize error handling

## 4. Test Organization

- Move standalone test files into the `tests/` directory
- Create organized test subdirectories matching source structure
- Remove redundant test files and consolidate to standard naming
- Clean up test data and use fixtures more effectively
- Update tests to reflect the Claude vision-based approach

## 5. Build and Configuration

- Update .gitignore to exclude all temporary files and directories
- Ensure all configuration templates are properly documented
- Standardize environment variable usage
- Remove MyScript-related configuration

## 6. Dependency Management

- Verify all dependencies in package.json and pyproject.toml
- Remove MyScript-related dependencies
- Document third-party tools and their installation
- Create reproducible development environment setup

## Implementation Priority

1. Update .gitignore to prevent temporary files from being tracked
2. Clean up temporary directories and duplicate test data
3. Consolidate documentation files and remove MyScript references
4. Move test files to proper test directory
5. Reorganize source code structure and remove unused MyScript code
6. Update documentation to reflect new organization and Claude vision approach

## Expected Outcomes

- Cleaner repository structure
- Better organized documentation reflecting the Claude vision-based approach
- More maintainable code organization
- Improved development experience
- Reduced repository size
- Better onboarding for new developers