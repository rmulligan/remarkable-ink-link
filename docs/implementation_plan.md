# InkLink Master Implementation Plan

This document consolidates all design deliverables into a phased roadmap, prioritizes key features, and assigns high‑level tasks for the engineering team.

---

## References

- Current architecture: `docs/current_state.md`  
- Web content pipeline: `docs/web_content_pipeline.md`  
- Google Docs pipeline: `docs/google_docs_pipeline.md`  
- Mixed content handling: `docs/mixed_content_handling.md`  
- Conversion strategy: `docs/conversion_strategy.md`  
- Cloud integration: `docs/cloud_integration.md`  
- Browser extension: `docs/browser_extension_design.md`  

---

## Phased Roadmap

### Phase 1: Core Web Content Enhancements  
Timeline: Weeks 1–2  
Objectives:  
- Implement multi‑stage extraction and sanitization  
- Build layout optimizer and modular HCL generators  
- Deliverables:  
  - Extended `WebScraperService` and cleaning modules  
  - `DocumentService` pagination and HCL unit tests  
Owners: Backend Team

### Phase 2: Google Docs Integration  
Timeline: Weeks 3–4  
Objectives:  
- Complete OAuth2 flow and token management  
- Structured HTML export and node parsing  
- Deliverables:  
  - `GoogleDocsService.fetch` enhancements  
  - Integration tests covering export → HCL → `.rm`  
Owners: Backend Team

### Phase 3: Mixed Content Module  
Timeline: Weeks 5–6  
Objectives:  
- Table schema extraction and HCL table rendering  
- Image scaling, caption support, and page‑break algorithm  
- Deliverables:  
  - `render_table` and `render_image` helpers  
  - Optimizer for mixed runs  
Owners: Backend Team

### Phase 4: Conversion Strategy Optimization  
Timeline: Weeks 7–8  
Objectives:  
- Optimize HCL → drawj2d pipeline (parallelism, caching)  
- Prototype direct `.rm` writer for basic text pages  
- Deliverables:  
  - Performance benchmarks  
  - Prototype Python writer for Lines v6  
Owners: Research & Prototyping Team

### Phase 5: Cloud Upload Robustness  
Timeline: Weeks 9–10  
Objectives:  
- Harden `RemarkableService.upload` with retry/backoff  
- Metadata handling and temp‑file fallback  
- Deliverables:  
  - End‑to‑end integration tests using `rmapi`  
Owners: Backend Team

### Phase 6: Browser Extension  
Timeline: Weeks 11–12  
Objectives:  
- Build manifest, content/background scripts, and UI  
- Implement share endpoint integration and preferences  
- Deliverables:  
  - Chrome/Firefox extension packages  
  - User acceptance testing  
Owners: Frontend Team

### Phase 7: Testing, CI, and Documentation  
Timeline: Weeks 13–14  
Objectives:  
- Expand unit/integration tests across all services  
- Configure CI pipeline and publish docs  
- Deliverables:  
  - GitHub Actions workflows  
  - Updated `docs/` site navigation  
Owners: QA & DevOps Team

---

## High‑Level Task Assignments

- **Backend Team:** Web pipeline, Google Docs, mixed content, cloud upload  
- **Research & Prototyping Team:** Direct `.rm` writer exploration, performance optimization  
- **Frontend Team:** Browser extension, share UI  
- **QA & DevOps Team:** Testing, CI, documentation deployment  

---

## Success Criteria

- All pipelines produce editable `.rm` files compatible with reMarkable v6  
- Automated tests cover ≥90% of service code  
- CI builds and publishes documentation on merge  
- Browser extension reaches version 1.0.0 with successful share flows  

---

*End of Master Plan*  
