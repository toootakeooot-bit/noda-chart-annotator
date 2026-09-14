# NODA Chart Annotator

Top-level contract: **NCA Boundary v1**  
Operational contract: **NCA Drawing Operation v1**  
Technical baseline: **NCA Live Draw Baseline v1 (subordinate to Boundary v1 / Drawing Operation v1)**

## Boundary v1

The active system boundary is fixed as follows:

- draw destination: **MT4① only**;
- canonical symbol identity: **XM MT4 symbol names**;
- drawing scope: **TL / HL / CH / direction arrow**;
- runtime drawing judgment: **NCA local logic (currently Python)**;
- ChatGPT is **not** part of the runtime drawing judgment path;
- MT4① renders the resulting drawing state;
- **TC is not used, is not a dependency, and no future TC integration is planned**;
- TC consumption is out of scope;
- market-hours logic is not used as a judgment/execution condition;
- NODA Engine remains a separate system and is not integrated into this drawing system;
- no order send/close/modify authority and no SL/TP modification authority.

`docs/BOUNDARY_V1.md` has precedence over older NCA documents where they conflict.

## Drawing Operation v1 — Normal Run

The active operating contract is fixed in `docs/DRAWING_OPERATION_V1.md`.

Normal operation is **user-initiated Normal Run**, not continuous monitoring or periodic polling.

At Normal Run, NCA:

1. reads closed-bar history for the target XM MT4① symbol on `D1 / H4 / H1 / M15`;
2. reconstructs structure chronologically from past to present;
3. determines the true rebuilt `current` TL and its true immediately prior `previous` TL;
4. generates and validates the new snapshot;
5. only after PASS replaces the target `NCA_DRAW__` objects on MT4①.

If rebuild or snapshot validation fails, the last valid drawing remains unchanged.

The operational rules are:

- XM MT4① symbols are supported in principle without a per-symbol allowlist/hard-code boundary;
- basic timeframes are **D1 / H4 / H1 / M15**;
- trigger = **user Normal Run**;
- continuous monitoring = **none**;
- periodic polling = **none**;
- TL display keeps **current + true immediately previous** generations rebuilt from closed-bar history;
- CH follows each parent TL generation;
- production managed-object prefix is **`NCA_DRAW__`**;
- objects outside the managed prefix are treated as user/manual objects and must not be touched;
- runtime drawing judgment stays in NCA local logic (currently Python), with MT4① as renderer.

## Existing Live Draw technical material

The existing Live Draw detector/lifecycle/renderer material remains available as technical assets, but conflicting clauses are subordinate to Boundary v1 and Drawing Operation v1.

Legacy technical material may still refer to timer-driven or continuous TEST/LIVE operation. Those references are **not the active Normal Run operating contract** where they conflict with `docs/DRAWING_OPERATION_V1.md`.

See:

- `docs/BOUNDARY_V1.md`
- `docs/DRAWING_OPERATION_V1.md`
- `docs/LIVE_DRAW_LIFECYCLE_V1.md`
- `docs/LIVE_DRAW_BASELINE_V1.md`
- `docs/LIVE_DRAW_DETECTOR_V1.md`
- `audit/BOUNDARY_V1_AUDIT_20260914.md`
- `audit/DRAWING_OPERATION_V1_AUDIT_20260914.md`
- `audit/NORMAL_RUN_HISTORY_REBUILD_AUDIT_20260914.md`
- `audit/LIVE_DRAW_BASELINE_V1_AUDIT.md`

## Teacher Benchmark

The previous Teacher PDF / Chatwork `分析共有` pipeline is retained as **Teacher Benchmark / Regression**. Teacher PDF agreement is not a Live Draw pass gate, and a week without Teacher chart material must not stop Normal Run.

Historical PDF tools and policies remain for benchmark use:

- `spec/PDF_ONLY_POLICY.md`
- `spec/PDF_GEOMETRY_POLICY.md`
- `tools/local_pdf_teacher_parser.py`
- `tools/pdf_geometry_extractor.py`
- `tools/pdf_geometry_extractor_compat.py`
- `tools/run_pdf_only_once.py`

Video / OpenAI API / Ollama remain outside the active runtime path unless separately approved in a later boundary revision.

## Hard boundaries

NCA must not emit or act on Entry, SL, TP, RR, Lot, Long/Short, Order, Ticket, or any trading decision. It must not write new detector logic or rules back into NODA Engine. Boundary changes require explicit owner approval and a new boundary revision.
