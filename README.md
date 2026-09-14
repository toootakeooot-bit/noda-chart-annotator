# NODA Chart Annotator

Top-level contract: **NCA Boundary v1**  
Technical baseline: **NCA Live Draw Baseline v1 (subordinate to Boundary v1)**

## Boundary v1

The active system boundary is fixed as follows:

- draw destination: **MT4① only**;
- canonical symbol identity: **XM MT4 symbol names**;
- drawing scope: **TL / HL / CH / direction arrow**;
- judgment owner: **ChatGPT**;
- MT4① receives and renders drawing instructions;
- **TC is not used, is not a dependency, and no future TC integration is planned**;
- TC consumption is out of scope;
- market-hours logic is not used as a judgment/execution condition;
- NODA Engine remains a separate system and is not integrated into this drawing system;
- no order send/close/modify authority and no SL/TP modification authority.

`docs/BOUNDARY_V1.md` has precedence over older NCA documents where they conflict.

## Existing Live Draw technical material

The existing Live Draw detector/lifecycle/renderer material remains available as technical assets, but conflicting clauses are subordinate to Boundary v1 and require later review before being treated as active implementation requirements.

Operational environments currently documented are:

- `TEST` — detector, selection, lifecycle, and renderer verification.
- `LIVE` — continuous drawing using logic verified in TEST.

See:

- `docs/BOUNDARY_V1.md`
- `audit/BOUNDARY_V1_AUDIT_20260914.md`
- `docs/LIVE_DRAW_BASELINE_V1.md`
- `docs/LIVE_DRAW_LIFECYCLE_V1.md`
- `docs/LIVE_DRAW_DETECTOR_V1.md`
- `audit/LIVE_DRAW_BASELINE_V1_AUDIT.md`

## Teacher Benchmark

The previous Teacher PDF / Chatwork `分析共有` pipeline is retained as **Teacher Benchmark / Regression**. Teacher PDF agreement is not a Live Draw pass gate, and a week without Teacher chart material must not stop Live Draw.

Historical PDF tools and policies remain for benchmark use:

- `spec/PDF_ONLY_POLICY.md`
- `spec/PDF_GEOMETRY_POLICY.md`
- `tools/local_pdf_teacher_parser.py`
- `tools/pdf_geometry_extractor.py`
- `tools/pdf_geometry_extractor_compat.py`
- `tools/run_pdf_only_once.py`

Video / OpenAI API / Ollama remain outside the active Live Draw path unless separately approved in a later boundary revision.

## Hard boundaries

NCA must not emit or act on Entry, SL, TP, RR, Lot, Long/Short, Order, Ticket, or any trading decision. It must not write new detector logic or rules back into NODA Engine. Boundary changes require explicit owner approval and a new boundary revision.
