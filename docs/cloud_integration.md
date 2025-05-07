# reMarkable Cloud Integration Flow

This document describes how InkLink uploads generated `.rm` files to the reMarkable Cloud using the `ddvk` fork of **rmapi**, including metadata considerations, retry logic, and error handling.

---

## 1. rmapi Setup & Authentication

- **Binary Path**  
  - Configured via `rmapi_path` in `RemarkableService`.  
- **First-Time Login**  
  ```bash
  rmapi login
  ```  
  - Stores credentials in `~/.config/remarkable/credentials.json`.  
- **Token Storage**  
  - `rmapi` manages OAuth tokens internally; no additional config required.

---

## 2. Upload Command Sequence

1. **Put File**  
   ```bash
   rmapi put <local_path>.rm <remote_folder>
   ```  
2. **Parse Output**  
   - Scan `stdout` for `ID: <document_id>`.  
3. **Rename Entry**  
   ```bash
   rmapi mv <document_id> "<desired_title>"
   ```  
4. **Folder Structure**  
   - Use default root (`/`) or custom subfolder.  
   - Create subfolders manually via `rmapi mkdir` if needed.

---

## 3. Required Metadata Files

- **.rm File Only**  
  - Cloud sync handles creation of metadata on-device.  
- **Local Metadata (optional)**  
  - For direct xochitl import, companion `content.json` and `metadata.json` may be generated via scripts like `pdf2rm.sh`.

---

## 4. Retry & Fallback Logic

- **Retry Parameters**  
  - Configurable attempt count and backoff in `CONFIG["retry"]`.  
- **Primary Attempt**  
  - Call `rmapi put` → on non-zero exit, capture `stderr`.  
- **Fallback Attempt**  
  - Copy file to temp path.  
  - Re-run `rmapi put` on fallback copy.  
- **Cleanup**  
  - Remove any temporary copies after each attempt.

---

## 5. Error Handling

- **Input Validation**  
  - Verify local file exists before upload.  
- **Executable Check**  
  - Error if `rmapi_path` is missing or not executable.  
- **Command Failure**  
  - On non-zero exit, log detailed `stderr`.  
  - Return failure to upstream call.  
- **ID Extraction Failure**  
  - Warn if `ID:` not found; skip rename step.  
- **Unexpected Exceptions**  
  - Wrap in `format_error("upload", ...)` via `retry_operation`.

---

## 6. Integration Points in InkLink

- **RemarkableService.upload()**  
  - Entry point after `.rm` generation.  
- **retry_operation**  
  - Wraps both primary and fallback upload methods.  
- **Logging**  
  - Detailed `info`, `warning`, and `error` at each step.  
- **Configuration**  
  - `upload_folder`, `rmapi_path`, and retry settings defined in `src/inklink/config.py`.

---

## 7. Testing & Validation

- **Unit Tests**  
  - Mock `subprocess.run` to simulate `put` and `mv` successes/failures.  
  - Validate temp-file fallback is invoked on failure.  
- **Integration Tests (Optional)**  
  - Local dry-run against test reMarkable Cloud account.  
  - Verify file appears with correct title and folder.
