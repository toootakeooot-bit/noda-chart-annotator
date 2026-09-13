# NODA Chart Annotator — PDF Geometry Direct Extraction v0.6.1

Purpose: reproduce Teacher-drawn chart geometry from the weekly chart PDF without video, OpenAI API, Ollama, or cloud AI.

## Pipeline
Chatwork -> Archive -> Queue -> Package -> deterministic PDF geometry extraction -> Teacher Geometry/Observation -> existing comparison/mapping stages -> MT4 Bridge/Renderer.

## v0.6.1 rules
- Teacher PDF/chart image is the primary source.
- Prefer embedded PDF vector drawings; use raster/Hough fallback when vector geometry is insufficient.
- Extract visible lines and parallel-pair candidates only.
- Do not infer Teacher rationale.
- Do not assert TL-vs-CH or HL semantic meaning from pixels alone.
- `UNKNOWN` is a valid result and does not stop geometry extraction.
- Video / OpenAI API / Ollama are HOLD and not used.
- FIB / Scenario auto-generation remains HOLD.
- No trading actions or Entry/SL/TP/RR/Lot/Order/Ticket fields.

## v0.6.1 compatibility fix
OpenCV `HoughLinesP` may return either `Nx1x4` or `Nx4` depending on build/version. v0.6.1 normalizes both shapes before raster parsing. This fixes the live Windows/OpenCV 5.x `IndexError: too many indices for array` seen on the 2026-08-15 Teacher package. Geometry-selection semantics are unchanged.

## Install into current live root
1. `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
2. `./setup/00_install_into_live_root.ps1`
3. Move to the live root.
4. `./setup/02_verify_pdf_geometry.ps1`
5. `./run_pdf_only_once.cmd`
