# Technical Debt Tracking

This document tracks technical debt items that need to be addressed in the codebase.

## Test Structure Refactoring

### E402 Module Import Order Issues
- **Status**: Tracked
- **Request ID**: req-1
- **Description**: Multiple test scripts use `sys.path` manipulation to enable imports, requiring E402 noqa comments
- **Impact**: Suppressed flake8 warnings instead of proper fix
- **Tasks**:
  1. Analyze current test structure
  2. Create proper test structure plan
  3. Set up proper Python packaging
  4. Convert standalone test scripts to pytest format
  5. Update test documentation
  6. Remove sys.path manipulations and E402 comments

### F841 Unused Variables in Tests
- **Status**: Tracked  
- **Request ID**: req-2
- **Description**: Multiple test files have F841 warnings for unused mock objects
- **Impact**: Suppressed flake8 warnings in test files
- **Tasks**:
  1. Audit test files for F841 warnings
  2. Refactor mock patterns in tests
  3. Remove unnecessary mock assignments
  4. Document mock usage patterns

## Security Vulnerabilities

### GitHub Dependabot Alerts
- **Status**: Active
- **Description**: 2 vulnerabilities found (1 critical, 1 moderate)
- **Action Required**: Review and update dependencies
- **Link**: https://github.com/rmulligan/remarkable-ink-link/security/dependabot

## Code Quality

### Black Formatting
- **Status**: Resolved
- **Description**: Applied consistent Python formatting across codebase

### Flake8 Compliance
- **Status**: Partially Resolved
- **Description**: Reduced from 250+ to ~20 issues, mainly in test files
- **Remaining Issues**: F841 and E402 in test files

## Architecture

### Handwriting Model Removal
- **Status**: Completed
- **Description**: Removed legacy handwriting model directory
- **Impact**: Reduced flake8 issues by 119

### Git LFS Configuration
- **Status**: Completed
- **Description**: Configured Git LFS for model files to reduce repository size

## Documentation

### Pre-commit Hooks
- **Status**: Active
- **Description**: Automated black and flake8 checks before commits
- **Note**: Use `--no-verify` to bypass when necessary