# Phase 6-J v0.6.1 Audit

## Decision
v0.5 Local VLM mode is HOLD because qwen3-vl:8b and qwen3-vl:4b both exceeded the 600-second verification timeout under CPU-only execution.

## v0.6.1 fixed mode
- Mode: `PDF_GEOMETRY_DETERMINISTIC`
- Video: not used.
- OpenAI API: not used.
- Ollama/VLM: not used.
- Cost: no cloud/API charge.
- Teacher rationale: UNKNOWN / deferred.

## Evidence separation
1. Direct geometry evidence: PDF vector or deterministic raster extraction.
2. Geometry relation: e.g. parallel pair candidate.
3. Rule mapping: only geometry portions that can be proved (for example R06 parallelism).
4. Teacher intent/rationale: never inferred; remains UNKNOWN.

## v0.6.1 live hotfix
The first 2026-08-15 live package reached raster fallback but failed because this Windows/OpenCV build returned `HoughLinesP` as a 2-D `Nx4` array while v0.6 assumed legacy `Nx1x4`. The compatibility shim normalizes both shapes before parsing. Geometry semantics are unchanged.

Offline regression using the same 2026-08-15 Teacher PDF now completes with `PDF_GEOMETRY_READY / PASS`, 230 line primitives, 785 parallel-pair candidates, selected mode `RASTER_FALLBACK`. These counts are extraction candidates, not validated NODA objects; filtering/mapping remains a later gate.

## Outputs
- `teacher_geometry.json`
- `teacher_observation.json`
- `geometry_debug/*.png`
- `pdf_only_status.json`

## Pass criteria
- Static Python compile PASS.
- Synthetic deterministic geometry self-test PASS.
- 2026-08-15 same-source PDF regression PASS after compatibility hotfix.
- Next live gate: apply v0.6.1 into the live root and rerun the oldest Teacher package; inspect primitive count and debug overlays before P5-5/MT4 integration.
