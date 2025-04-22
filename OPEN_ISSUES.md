# Open Issues Outline

 ## 1. Testing

 ### 1.1 High Priority
 - **#21** – Test missing for plain text input with mixed valid/invalid content (priority: high)

 ### 1.2 Suggestions / Low Priority
 - **#49** – suggestion (testing): Add test cases for URLs with no path
 - **#48** – suggestion (testing): Add test cases for URLs with no path
 - **#47** – suggestion (testing): Consider expanding parametrized test cases

 ## 2. Code-Quality

 ### 2.1 Medium Priority
 - **#31** – issue (code-quality): We’ve found these issues which require attention
 - **#27** – issue (code-quality): We’ve found these issues which require attention

 ### 2.2 Low Priority
 - **#42** – Extract duplicate code into function [×2]
 - **#41** – Avoid conditionals in tests.
 - **#40** – We’ve found these issues.
 - **#39** – Use named expression to simplify assignment and conditional [×4]
 - **#37** – We’ve found these issues.
 - **#34** – Extract duplicate code into function [×2]
 - **#33** – We’ve found these issues.
 - **#32** – We’ve found these issues.
 - **#30** – Use named expression to simplify assignment and conditional [×4]
 - **#28** – Extract code out into method
 - **#26** – Use named expression to simplify assignment and conditional
 - **#25** – Avoid conditionals in tests.
 - **#24** – Avoid conditionals in tests.

 ## 3. Complexity (priority: medium)
 - **#22** – Consider refactoring the `_upload_with_n_flag` method to extract temporary file handling and subprocess execution into helper functions.
 - **#23** – Consider extracting the HTML parsing logic into a shared helper function to be used by both GoogleDocsService and WebScraperService.
 - **#36** – Consider refactoring the long content loop in `create_hcl` into separate helper methods for different content types.
 - **#38** – Consider refactoring the long content loop in `create_hcl` into separate helper methods for different content types.

---

# InkLink Implementation Plan (April 21, 2025)

This document provides a structured implementation plan for continued development of the InkLink project, particularly focusing on MyScript iink SDK integration and the UI-based tag actions system.

## Priority Tasks

### 1. MyScript iink SDK Integration

1. **Environment Setup**
   - [ ] Install iink-ts npm package
   - [ ] Add required DOM structure in frontend
   - [ ] Securely store MyScript API credentials (Application Key and HMAC Key)

2. **Basic Integration**
   - [ ] Create frontend component for ink capture and rendering
   - [ ] Initialize iinkTS editor with proper configuration
   - [ ] Implement basic handwriting capture functionality
   - [ ] Add content export capabilities (to text, JIIX format)

3. **Client-Server Communication**
   - [ ] Implement error handling for network connectivity issues
   - [ ] Add retry mechanisms for failed requests
   - [ ] Create user feedback for processing status

4. **Backend Integration**
   - [ ] Create HandwritingRecognitionService implementation using the updated interface
   - [ ] Design data flow between frontend and backend components

### 2. UI-Based Tag Action System

1. **Tag Management UI**
   - [ ] Create UI components for tag selection/creation
   - [ ] Design tag palette or dropdown for common tags
   - [ ] Implement UI for custom tag creation

2. **Content Selection and Association**
   - [ ] Implement content selection functionality
   - [ ] Create data model for tag-content associations
   - [ ] Design database schema for storing associations

3. **Action Triggering UI**
   - [ ] Create UI elements for triggering actions on tagged content
   - [ ] Design action selection interface
   - [ ] Implement confirmation dialogs for actions

4. **Action Execution**
   - [ ] Implement handlers for different action types
   - [ ] Create content retrieval mechanisms
   - [ ] Build processing pipeline for tagged content

### 3. Documentation and Testing

1. **GitHub Wiki Creation**
   - [ ] Enable wiki in repository settings
   - [ ] Clone wiki repository
   - [ ] Create initial structure following the guidelines in codex.md
   - [ ] Document MyScript integration approach
   - [ ] Document tag-based action implementation

2. **Testing Strategy**
   - [ ] Create unit tests for HandwritingRecognitionService
   - [ ] Implement integration tests for tag-content association
   - [ ] Test across multiple browsers (Chrome, Firefox, Safari, Edge)
   - [ ] Test with various network conditions

## Implementation Guidelines

### MyScript iink SDK Best Practices

1. **Authentication**
   - Store API credentials securely
   - Use environment variables for sensitive information
   - Implement proper HMAC authentication

2. **Configuration**
   - Start with minimal configuration focused on text content
   - Gradually extend to support math, diagrams, etc.
   - Configure proper language support (start with 'en_US')

3. **Network Considerations**
   - Always handle potential network failures gracefully
   - Provide clear user feedback for server-side processing
   - Consider implementing offline mode with limited functionality

### Tag System Architecture

1. **Data Model**
   - Tags should be stored separately from ink content
   - Create associations between tags and content identifiers
   - Support hierarchical tag relationships if needed

2. **UI Design Principles**
   - Keep tag UI separate from ink canvas
   - Use consistent visual language for tags
   - Ensure tag selection is intuitive and accessible

3. **Action Execution**
   - Actions should be modular and extensible
   - Provide clear progress indication for long-running actions
   - Include error handling and recovery options

## Technical Constraints

1. **Browser Compatibility**
   - Support latest versions of Chrome, Firefox, Safari, Edge
   - Be mindful of different touch/stylus input behaviors

2. **Performance Considerations**
   - Optimize network requests to minimize latency
   - Handle large documents efficiently
   - Consider pagination or lazy loading for large content

3. **Security Requirements**
   - Protect MyScript API credentials
   - Validate user input for custom tags
   - Implement proper authentication for user-specific content

## References

1. Updated MyScript integration details in `codex.md`
2. Revised interface for HandwritingRecognitionService in `src/inklink/services/interfaces.py`
3. GitHub wiki maintenance instructions in `codex.md`

---

The coding agent should use this plan to guide implementation, updating this document as tasks are completed and new requirements are identified. Regular commits with descriptive messages should be made to track progress.