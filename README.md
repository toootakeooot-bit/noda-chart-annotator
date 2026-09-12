# NODA Chart Annotator — PDF Geometry Direct Extraction v0.6

Purpose: reproduce Teacher-drawn chart geometry from the weekly chart PDF without video, OpenAI API, Ollama, or cloud AI.

## Pipeline
Chatwork -> Archive -> Queue -> Package -> deterministic PDF geometry extraction -> Teacher Geometry/Observation -> existing comparison/mapping stages -> MT4 Bridge/Renderer.

## v0.6 rules
- Teacher PDF/chart image is the primary source.
- Prefer embedded PDF vector drawings; use raster/Hough fallback when vector geometry is insufficient.
- Extract visible lines and parallel-pair candidates only.
- Do not infer Teacher rationale.
- Do not assert TL-vs-CH or HL semantic meaning from pixels alone.
- `UNKNOWN` is a valid result and does not stop geometry extraction.
- Video / OpenAI API / Ollama are HOLD and not used.
- FIB / Scenario auto-generation remains HOLD.
- No trading actions or Entry/SL/TP/RR/Lot/Order/Ticket fields.

## Install into current live root
1. `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
2. `./setup/00_install_into_live_root.ps1`
3. Move to the live root.
4. `./setup/01_install_pdf_geometry.ps1`
5. `./setup/02_verify_pdf_geometry.ps1`
6. `./run_pdf_only_once.cmd`
