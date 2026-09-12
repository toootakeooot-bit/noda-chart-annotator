# Phase 6-J v0.6 Audit

## Decision
v0.5 Local VLM mode is HOLD because qwen3-vl:8b and qwen3-vl:4b both exceeded the 600-second verification timeout under CPU-only execution.

## v0.6 fixed mode
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

## Outputs
- `teacher_geometry.json`
- `teacher_observation.json`
- `geometry_debug/*.png`
- `pdf_only_status.json`

## Pass criteria
- Static Python compile PASS.
- Synthetic deterministic geometry self-test PASS.
- Next live gate: run against oldest Teacher PDF package and inspect primitive count/debug overlays.
