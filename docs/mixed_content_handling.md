# Mixed Content Handling Module

This document defines requirements and strategies for parsing and laying out pages containing mixed content types (text, images, tables) to generate optimal reMarkable ink documents.

---

## 1. Table Parsing and Rendering

- **Structured Table Extraction**  
  - Detect `<table>` elements in `WebScraperService` and `GoogleDocsService`.  
  - Extract rows, columns, cell content, and optional headers.  
- **Table Schema**  
  ```yaml
  type: table
  headers: [ "H1", "H2", ... ]
  rows:
    - [ "R1C1", "R1C2", ... ]
    - [ ... ]
  ```
- **HCL Table Rendering**  
  - Compute column widths proportional to page width minus margins.  
  - Draw grid lines:  
    ```hcl
    puts "line x1 y1 x2 y1"  # top border
    puts "line x1 yN x2 yN"  # bottom border
    puts "line xi y1 xi yN"  # column dividers
    puts "line x1 yi x2 yi"  # row dividers
    ```  
  - Position cell text with padding inside each cell.

---

## 2. Image Placement & Scaling

- **Aspect‑Preserving Scaling**  
  - Calculate max image width = page width − 2×margin.  
  - Scale height = original_height × (scaled_width / original_width).  
- **Placement Options**  
  - Inline with text flow: break paragraphs, insert image block.  
  - Full‑width break: center image horizontally with caption below.  
- **Caption Support**  
  - Attach `caption` field in content schema.  
  - Render caption in italic body font below image with smaller font size.

---

## 3. Mixed Flow Content Optimizer

- **Content Runs**  
  - Treat text, image, and table blocks as discrete runs.  
  - Compute run height based on font size or image/table dimensions.  
- **Page‑Break Algorithm**  
  - Accumulate run heights until page bottom margin.  
  - If next run doesn’t fit:
    - For tables longer than a page, split rows across pages with repeated headers.  
    - For images larger than remaining space, break before or scale down.  
- **Margin Adaptation**  
  - Reduce top margin slightly on split tables to maximize usable area.  
  - Adjust inter‑run spacing to fill gaps.

---

## 4. HCL Extensions for Mixed Content

- **Modular Functions**  
  - `render_table(table_schema, x, y)`  
  - `render_image(path, x, y, width, height)`  
- **Caption & Labeling**  
  - Number tables and images sequentially.  
  - Generate footnote reference list at document end if needed.
- **Error Handling**  
  - Log warnings for oversized tables/images.  
  - Fallback: convert table to text list if rendering fails.

---

## 5. Integration Points

1. **Scraping Phase** → augmented schema with `type: table`, `type: image`.  
2. **DocumentService.create_hcl()** → detect mixed blocks and call new rendering functions.  
3. **Layout Optimizer** → invoked before HCL write to determine page breaks.  
4. **Testing** → unit tests for table schema parsing, image scaling, and page‐break logic.

