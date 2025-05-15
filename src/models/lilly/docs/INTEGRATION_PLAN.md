# Integration Plan: Proton and Google Services

This document outlines the integration strategy to enable Lilly to navigate and interact with Proton Mail, Proton Calendar, and Google Drive.

## 1. Overview

Lilly will be equipped with three new adapters:
1. **Proton Mail Adapter**: Access emails, search, and manage folders
2. **Proton Calendar Adapter**: View, create, and modify calendar events
3. **Google Drive Adapter**: Browse, search, and interact with files

These adapters will work through a combination of:
- Official APIs where available
- Browser automation for functionality not exposed via APIs
- Command-line tools for local interactions

## 2. Authentication Strategy

### Proton Services (Mail & Calendar)

Proton offers programmatic access through:
1. **Proton Bridge**: Command-line application providing IMAP/SMTP access to Proton Mail
2. **Proton API**: REST API for advanced functionality (requires developer access)

Authentication flow:
1. User configures Proton Bridge with their credentials
2. Lilly adapters connect to the IMAP/SMTP service exposed by Bridge
3. OAuth2 flow for Proton API access (if available)
4. Secure credential storage using environment variables and/or keyring

### Google Drive

Google Drive offers comprehensive API access:
1. **Google Drive API**: REST API for file operations
2. **Google OAuth2**: Authentication system for API access

Authentication flow:
1. Register application in Google Cloud Console
2. Implement OAuth2 authentication flow
3. Store and refresh tokens securely
4. Use service account for background operations (optional)

## 3. Adapter Implementations

### 3.1 Proton Mail Adapter

**Core Functions**:
- Connect to Proton Bridge via IMAP
- List mailboxes and emails
- Search emails by various criteria
- Download and parse email content
- Extract entities for knowledge graph
- Send emails via SMTP

**Implementation Strategy**:
1. Use Python's `imaplib` and `email` modules to interact with Proton Bridge
2. Create abstraction layer for common email operations
3. Implement content parsing for both plain text and HTML emails
4. Add entity extraction and knowledge graph integration

### 3.2 Proton Calendar Adapter

**Core Functions**:
- View upcoming events
- Add new calendar events
- Modify existing events
- Set reminders and notifications
- Sync with knowledge graph for context-aware scheduling

**Implementation Strategy**:
1. Use CalDAV protocol via Proton Bridge (if supported)
2. Alternatively, use browser automation with Selenium for calendar access
3. Create a standardized calendar object model
4. Implement bi-directional sync with knowledge graph

### 3.3 Google Drive Adapter

**Core Functions**:
- List files and folders
- Search by filename or content
- Download files
- Create and upload new files
- Share files and manage permissions
- Extract content for knowledge graph

**Implementation Strategy**:
1. Use Google Drive API through official Python client library
2. Implement caching for improved performance
3. Create file content extractors based on file type
4. Add vectorization of document content for semantic search
5. Implement knowledge graph integration for documents

## 4. Knowledge Graph Integration

Each adapter will enrich Lilly's knowledge graph by:

1. **Creating Entity Types**:
   - `Email`: Representing email messages
   - `EmailFolder`: Representing mail organization
   - `Contact`: People from email and calendar
   - `Event`: Calendar events
   - `File`: Google Drive files
   - `Folder`: Google Drive folders

2. **Establishing Relationships**:
   - `SENT_BY`: Who sent an email
   - `SENT_TO`: Recipients of emails
   - `MENTIONS`: Entities mentioned in content
   - `SCHEDULED_WITH`: People involved in events
   - `CONTAINS`: Parent-child relationship for folders
   - `REFERENCES`: Cross-references between documents

3. **Temporal Context**:
   - Connect emails and events to a timeline
   - Enable queries like "find documents related to the meeting last Tuesday"
   - Track interaction history with specific contacts

## 5. Command Line Interface

New CLI commands will be added to `main.py`:

```
# Email commands
lilly email list [--folder=FOLDER] [--count=N] [--filter=FILTER]
lilly email search QUERY [--folder=FOLDER]
lilly email read MESSAGE_ID
lilly email send --to=RECIPIENT --subject=SUBJECT [--body=FILE]

# Calendar commands
lilly calendar view [--start=DATE] [--end=DATE]
lilly calendar add --title=TITLE --start=TIME --end=TIME [--details=DETAILS]
lilly calendar update EVENT_ID [--title=TITLE] [--start=TIME] [--end=TIME]

# Google Drive commands
lilly drive list [--folder=FOLDER]
lilly drive search QUERY
lilly drive download FILE_ID [--output=PATH]
lilly drive upload PATH [--folder=FOLDER_ID]
```

## 6. Integration with Lilly's Workflow

### 6.1 Email Workflow

1. User asks Lilly about recent emails on a topic
2. Lilly queries the knowledge graph for relevant emails
3. If needed, fetches additional details via Proton Mail adapter
4. Presents summarized information with option to read full content
5. Updates knowledge graph with new entities from email content

### 6.2 Calendar Workflow

1. User asks Lilly about upcoming meetings
2. Lilly queries calendar adapter for events
3. Provides context-aware information (e.g., "You have a meeting with John tomorrow, and here are related documents from your last meeting")
4. Enables scheduling new events with natural language
5. Syncs event information with knowledge graph

### 6.3 Google Drive Workflow

1. User asks Lilly to find files on a specific topic
2. Lilly searches Google Drive with semantic understanding
3. Presents relevant files with context from knowledge graph
4. Can extract information from files to answer questions
5. Enables creating new documents based on knowledge

## 7. Implementation Phases

### Phase 1: Core Adapters
- Basic authentication flows
- Essential read-only functionality
- Simple CLI commands

### Phase 2: Knowledge Graph Integration
- Entity extraction from content
- Relationship mapping
- Temporal context

### Phase 3: Advanced Features
- Writing and modification capabilities
- Cross-service integrations
- Natural language interfaces

### Phase 4: User Experience Enhancements
- Context-aware suggestions
- Proactive notifications
- Workflow optimization

## 8. Technical Requirements

- **Python Libraries**:
  - `imaplib`, `email`: For IMAP/SMTP operations
  - `google-api-python-client`: For Google Drive API
  - `selenium` (optional): For browser automation
  - `caldav`: For CalDAV calendar access
  - `langchain`: For content extraction and processing
  - `pydantic`: For data modeling
  - `cryptography`: For secure credential handling

- **External Dependencies**:
  - Proton Bridge (installed and configured)
  - Google API credentials
  - Neo4j for knowledge graph storage

## 9. Security Considerations

- No storage of raw passwords
- Use of OAuth tokens with appropriate scopes
- Secure token storage using system keyring
- Encryption of cached data
- Clear guidelines on data usage and privacy

## 10. Testing Strategy

- Unit tests for adapter functionality
- Integration tests with mock services
- End-to-end tests with real accounts (using test accounts)
- Security audits for credential handling

## Next Steps

1. Set up development environment with required dependencies
2. Create skeleton adapters with authentication flows
3. Implement basic read operations for each service
4. Develop knowledge graph integration model
5. Build CLI interface for service interaction
6. Create documentation and usage examples