# Phase 6-J v0.6 PDF Geometry Policy

## Purpose
Extract Teacher-drawn chart geometry directly from weekly PDF/chart material without video, OpenAI API, Ollama, or any cloud AI.

## Evidence boundary
- Directly visible/drawable geometry may be extracted.
- PDF vector geometry is preferred when enough usable primitives exist.
- Otherwise raster geometry is detected deterministically from rendered PDF pages.
- The extractor MUST NOT invent why the Teacher selected a line.
- TL/CH/HL semantic assignment remains UNKNOWN unless a later rule-mapping stage can prove it.
- Parallel-line geometry may be tagged `PARALLEL_PAIR_CANDIDATE`; TL-vs-CH side remains UNKNOWN.
- FIB/Scenario automatic generation remains HOLD.

## Hard trading boundary
Never output Entry, SL, TP, RR, Lot, Long/Short, Order, Ticket, or trading actions.

## Outputs
- `teacher_geometry.json`: raw deterministic geometry evidence.
- `teacher_observation.json`: conservative observation wrapper for downstream compatibility.
- `geometry_debug/*.png`: automatic visual overlays for audit.
- `pdf_only_status.json`: run status.
