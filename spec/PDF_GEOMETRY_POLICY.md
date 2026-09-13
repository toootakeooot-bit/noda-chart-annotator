# Phase 6-J v0.6 PDF Geometry Policy — Teacher Benchmark Scope

> Baseline note: under `NCA Live Draw Baseline v1`, this policy is retained for **Teacher Benchmark / Regression only**. PDF geometry is not the primary Live Draw input and is not a required Live Draw gate.

## Purpose
Extract Teacher-drawn chart geometry directly from weekly PDF/chart material without video, OpenAI API, Ollama, or cloud AI for benchmark/regression use.

## Evidence boundary
- Directly visible/drawable geometry may be extracted.
- PDF vector geometry is preferred when enough usable primitives exist.
- Otherwise raster geometry is detected deterministically from rendered PDF pages.
- The extractor MUST NOT invent why the Teacher selected a line.
- TL/CH/HL semantic assignment remains UNKNOWN unless a later rule-mapping stage can prove it.
- Parallel-line geometry may be tagged `PARALLEL_PAIR_CANDIDATE`; TL-vs-CH side remains UNKNOWN.
- FIB/Scenario automatic generation remains HOLD.

## Live Draw boundary
- Live Draw primary input is MT4 OHLC.
- Teacher PDF agreement is not a Live Draw pass condition.
- Missing or ambiguous Teacher material must not stop Live Draw.
- Teacher benchmark outputs must not overwrite Live Draw snapshots or lifecycle state.

## Hard trading boundary
Never output Entry, SL, TP, RR, Lot, Long/Short, Order, Ticket, or trading actions.

## Benchmark outputs
- `teacher_geometry.json`: raw deterministic geometry evidence.
- `teacher_observation.json`: conservative observation wrapper for benchmark compatibility.
- `geometry_debug/*.png`: automatic visual overlays for audit.
- `pdf_only_status.json`: benchmark run status.
