# Conversion Strategy for `.rm` Files

This document evaluates two primary methods for producing reMarkable‑compatible `.rm` pages: the existing HCL → PDF → `.rm` pipeline using **drawj2d**, and a direct `.rm` generation approach informed by **rmscene** or similar libraries.

---

## 1. HCL → PDF → `.rm` via drawj2d

**Overview**  
- Generate an HCL script describing layout (text, images, vectors).  
- Use drawj2d (Java) to rasterize content into Lines v6 `.rm` stroke data.  
- Optionally package pages into a `.zip` for cloud upload.

**Pros**  
- Mature rendering engine optimized for fidelity.  
- Familiar HCL DSL for layout control.  
- Offloads complex PDF rendering to Java toolchain.  
- Strong community usage in PDF‑to‑reMarkable workflows.

**Cons**  
- Indirect: intermediate PDF increases I/O and temp storage.  
- Latency: PDF rendering + conversion can be slow for large docs.  
- Dependency on Java + drawj2d maintenance.  
- Limited control over stroke parameters beyond HCL abstractions.

**Performance**  
- Typical throughput: ~1 page/second on standard hardware.  
- Memory overhead due to JVM startup and PDF parsing.  
- Parallelism: possible but requires multiple drawj2d instances.

---

## 2. Direct `.rm` Generation

**Overview**  
- Build `.rm` stroke layers programmatically using Python (e.g., extending `rmscene` or writing new writer).  
- Map structured content directly to vector primitives (lines, text strokes).  
- Emit binary `.rm` files without intermediate formats.

**Pros**  
- Eliminates PDF intermediary → reduced I/O and storage.  
- Fine‑grained control over stroke attributes (width, pressure).  
- Single‑language pipeline (Python).  
- Potential for faster generation (< 0.5 sec/page) with optimized writer.

**Cons**  
- Significant development effort: must implement binary format writer for Lines v6.  
- Limited existing libraries: `rmscene` supports reading, not writing.  
- Risk of format drift with reMarkable firmware updates.  
- Lacks proven rendering quality out of the box.

**Performance**  
- CPU‑bound stroke generation; can vectorize loops in C extensions.  
- Lower memory footprint vs JVM approach.  
- Easily parallelizable in Python threads or processes.

---

## 3. Hybrid & Other Options

- **PDF direct injection**: strip PDF strokes into `.rm` layers via custom converter.  
- **SVG → `.rm`**: render SVG with headless browser, convert to vector strokes.  
- **Third‑party tools**: evaluate `pdf2rm.sh` and community forks for direct metadata packaging.

---

## 4. Decision Factors

- **Fidelity vs. Control**: drawj2d offers high‑quality PDF fidelity; direct writer offers deeper control.  
- **Development Cost**: HCL pipeline near‑term ready; direct writer is long‑term investment.  
- **Performance Needs**: high‑volume conversion favors direct generation.  
- **Maintenance**: Java dependency vs custom Python codebase.

---

## 5. Recommendation

Begin by optimizing the HCL → drawj2d workflow (parallelism, caching). In parallel, prototype a minimal direct `.rm` writer for basic text / vector pages to assess effort and performance gains.  
