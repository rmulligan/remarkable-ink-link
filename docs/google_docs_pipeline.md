# Google Docs Integration Pipeline

This document describes enhancements for the Google Docs content pipeline, including authentication, structured extraction, error handling, and integration with the conversion workflow.

---

## 1. OAuth2 Authentication Flow

**Configuration:**  
- `GOOGLE_CREDENTIALS_PATH`: path to client secrets JSON  
- `GOOGLE_TOKEN_PATH`: path to store user tokens (`token.json` by default)  

**Steps:**  
1. **Initial Authorization**  
   - User consent via local web server (`InstalledAppFlow.run_local_server`).  
   - Scopes:  
     - `https://www.googleapis.com/auth/drive.readonly`  
2. **Token Persistence & Refresh**  
   - Load existing credentials from `token.json`.  
   - If expired with refresh token: call `creds.refresh(Request())`.  
   - Otherwise launch consent flow again.  
   - Save updated `creds.to_json()` for subsequent runs.  
3. **Library Initialization**  
   - Build Drive service via `googleapiclient.discovery.build("drive", "v3", credentials=creds)`.  
   - Log warnings if client libraries are missing.

---

## 2. Structured Content Extraction

**Source:** `src/inklink/services/google_docs_service.py`  

- **Export as HTML**  
  - `drive_service.files().export(mimeType="text/html")` wrapped in `retry_operation`.  
- **HTML Parsing**  
  - `BeautifulSoup(html, "html.parser")`  
  - Extract document title (`<title>`, OpenGraph metadata fallback).  
  - Identify container (`soup.body` or full document).  
- **Tag Processing**  
  - Delegate to `parse_html_container(container, base_url)` for:  
    - Headings (`h1–h6` → `heading` nodes)  
    - Paragraphs  
    - Lists  
    - Images (src URLs, captions)  
    - Tables (if present)  
- **Output:**  
  ```json
  {
    "title": "Document Title",
    "structured_content": [ ...nodes... ],
    "images": [ {"src": "...", "alt": "..."}, ... ]
  }
  ```

---

## 3. Error Handling & Fallbacks

- Wrap fetch in `try/except` around export and parsing.  
- On failures:  
  - Log error via `logger.error(format_error(...))`.  
  - Return minimal fallback content:  
    ```json
    {
      "title": url_or_id,
      "structured_content": [
        {
          "type": "paragraph",
          "content": "Could not fetch Google Docs doc URL_OR_ID: ERROR_MESSAGE"
        }
      ],
      "images": []
    }
    ```
- Ensure retry logic for transient API errors.

---

## 4. Integration with Conversion Pipeline

1. **Entry Point:**  
   - Client or server invokes `GoogleDocsService.fetch(url_or_id)`.  
2. **Normalization:**  
   - Validate returned `structured_content` schema.  
3. **HCL Generation:**  
   - Pass `structured_content` and `images` into `DocumentService.create_hcl()`.  
   - Include document title as header block.  
4. **Layout & Pagination:**  
   - Run layout optimizer for page breaks and image placement.  
5. **Conversion & Upload:**  
   - Generate `.rm` via `drawj2d`.  
   - Upload via `RemarkableService.upload()`.  

---

## 5. Testing & Validation

- Unit tests for:  
  - `_extract_doc_id()` variations  
  - Successful `fetch()` with mocked HTML  
  - Error path returns fallback content  
- Integration tests:  
  - Round‑trip export → parse → HCL → `.rm` generation  
