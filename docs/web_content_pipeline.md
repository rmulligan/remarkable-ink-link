# Enhanced Web Content Pipeline

This document defines the improved stages for converting web pages into reMarkable ink documents.

---

## 1. WebScraperService Improvements

**Source:** `src/inklink/services/web_scraper_service.py`

- **Multi‑stage extraction:**  
  1. Primary fetch via `requests` + robust headers.  
  2. Reader‑mode fallback using `readability-lxml` (if available).  
  3. HTML container detection (`<main>`, `<article>`, `<section>`).  
- **Title enrichment:**  
  - Direct parsing of OpenGraph, Twitter, `<title>`, and `<h1>`.  
  - Truncate overly long titles.  
- **Image handling:**  
  - Collect image URLs + captions.  
  - Pre‑filter by size/aspect ratio.  
  - Queue for download and local caching.

---

## 2. Content Cleaning & Normalization

- **HTML sanitization:**  
  - Strip scripts, styles, ads, and trackers.  
  - Normalize whitespace and line breaks.  
- **Structured content schema:**  
  - Standardize node types: `heading`, `paragraph`, `list`, `code`, `image`, `table`.  
  - Convert legacy list formats to bullet items.  
- **Link rewriting:**  
  - Inline display of link text with footnote numbering.  
  - Append footnote list at the end of document.

---

## 3. Layout Optimizer

**Source:** `src/inklink/services/document_service.py`

- **Adaptive pagination:**  
  - Measure text blocks vs. page height.  
  - Insert page breaks before overflow.  
- **Dynamic font sizing:**  
  - Heading hierarchy (`h1→36pt`, `h2→28pt`, `h3→24pt`, default body 20pt).  
  - Auto‑scale for long headings.  
- **Margin & gutter control:**  
  - Configurable per device (`TEMP_DIR`, Pro vs. standard).  
- **Table support (future):**  
  - Detect `<table>` nodes → convert to monospace grid.  
  - Compute column widths by content length.

---

## 4. HCL Script Enhancements

- **Modular HCL generation:**  
  - Separate functions for headers, QR code, content blocks, and footer.  
  - Enable unit testing of each HCL section.  
- **List grouping:**  
  - Render nested lists with indent levels.  
  - Support numbered and bulleted lists.  
- **Code block styling:**  
  - Draw background rectangle + border.  
  - Use monospace `code_font` with customizable size.  
- **Image placement:**  
  - Calculate scaled dimensions for page width.  
  - Support captions below images.  
- **Footnotes & links:**  
  - Generate numbered footnotes section at document end.  
- **Performance logging:**  
  - Preview first 200 chars of HCL for rapid debugging.  

---

## 5. Integration Points

- **After scrape:** feed normalized `structured_content` into `DocumentService.create_hcl()`.  
- **Before conversion:** run layout optimizer to adjust `y_pos` and insert breaks.  
- **Testing:** add unit tests for new cleaning, pagination, and HCL modules.  
