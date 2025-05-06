# InkLink API Documentation

## /ingest Endpoint

**POST /ingest**

Ingest content from browser extension, Siri shortcut, or web UI.

**Request Body (application/json):**
- `type`: `"web"`, `"note"`, `"shortcut"`, etc. (string, required)
- `title`: Title of the content (string, required)
- `content`: Main content (text, HTML, markdown, etc., required)
- `metadata`: Optional dictionary (e.g., `source_url`, `tags`, etc.)

**Example:**
```json
{
  "type": "web",
  "title": "Interesting Article",
  "content": "<h1>Example</h1><p>Some content...</p>",
  "metadata": {
    "source_url": "https://example.com",
    "tags": ["reading", "reference"]
  }
}
```

**Response:**
- `{"status": "accepted"}` on success
- `{"error": "...error message..."}` on failure

**Notes:**
- This endpoint is intended for integration with browser extensions, Siri shortcuts, and the web UI.
- Content is queued for further processing and delivery to the device or index notebook.