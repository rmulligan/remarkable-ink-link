# InkLink Browser Extension Architecture

This document outlines the design of a browser extension for InkLink that enables users to share web content directly to their reMarkable via the InkLink server.

---

## 1. Manifest Configuration

```json
{
  "manifest_version": 3,
  "name": "InkLink Share",
  "version": "1.0.0",
  "permissions": [
    "activeTab",
    "storage",
    "notifications",
    "scripting"
  ],
  "host_permissions": [
    "<all_urls>",
    "https://<inklink-server>/*"
  ],
  "background": {
    "service_worker": "background.js"
  },
  "action": {
    "default_popup": "popup.html",
    "default_icon": "icons/icon-48.png"
  },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content.js"]
    }
  ],
  "options_page": "options.html"
}
```

---

## 2. Authentication Flow

- **Token Storage:**  
  - Use `chrome.storage.local` to save `apiToken` and `serverUrl`.  
- **OAuth Redirect:**  
  - Popup opens `<serverUrl>/auth/login?redirect_uri=<extension-callback>`.  
  - Background worker listens for redirect, extracts token from URL parameters.  
- **Manual Entry Fallback:**  
  - Options page allows pasting a permanent API key.

---

## 3. UI Components

- **Popup (`popup.html` + `popup.js`):**  
  - Show auth status (signed in/guest).  
  - Button: _Share This Page_.  
  - Display last share status or error.  
- **Options Page (`options.html` + `options.js`):**  
  - Fields: InkLink Server URL, API Token, default device, formatting preferences.  
  - Save to `chrome.storage.local`.

---

## 4. Content Extraction

- **Content Script (`content.js`):**  
  - On request, gather:  
    - `document.title`  
    - `window.location.href`  
    - Main article HTML via `document.querySelector('article')` or full `document.body.innerHTML`.  
  - Send message to background: `{ type: 'extract', payload }`.

---

## 5. Background Logic

- **Message Listener (`background.js`):**  
  - Handle `'extract'` → call server `/share` endpoint.  
  - Build POST JSON:  
    ```json
    {
      "url": "...",
      "html": "...",
      "options": {
        "includeImages": true,
        "fontSize": 20,
        "margin": 20
      }
    }
    ```
  - Append `Authorization: Bearer <apiToken>` header.  
  - On success: show notification "Sent to reMarkable".  
  - On error: show notification with error message.

---

## 6. Server Endpoints

- **POST `/share`**  
  - Accepts JSON `{ url, html, options }`.  
  - Returns `{ success: true, jobId }` or error.  
- **GET `/auth/login` & callback**  
  - Standard OAuth2 for initial login.

---

## 7. User Preferences

- **Options Schema:**  
  - `defaultFontSize` (px),  
  - `defaultMargin` (px),  
  - `includeImages` (boolean),  
  - `autoPaginate` (boolean).  
- **Application:**  
  - Background reads preferences on each share request.

---

## 8. Messaging & Error Handling

- **Messaging:**  
  - Content → Background via `chrome.runtime.sendMessage`.  
  - Background → Popup via `chrome.runtime.onMessage`.  
- **Errors:**  
  - Network failures: retry once, then notify.  
  - Auth failures: prompt re-login.

---

## 9. Security Considerations

- Restrict host permissions to configured server.  
- Sanitize HTML before sending to server.  
- Use HTTPS only.

---

## 10. Extensibility

- Support domain-specific templates.  
- Add context-menu item for sharing selected text.  
- Future: page‑annotation mode.
