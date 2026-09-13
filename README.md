# NODA Chart Annotator

Primary mode: **NCA Live Draw Baseline v1**

## Purpose

NODA Chart Annotator (NCA) uses MT4 OHLC to recognize NODA-compatible market structure and draw TL / CH / Zone for the initial instruments `USDJPY`, `GOLD`, and `US100` on `D1`, `H4`, `H1`, and `M15`.

The operational environments are:

- `TEST` — detector, selection, lifecycle, and renderer verification.
- `LIVE` — continuous drawing using logic verified in TEST.

Timeframe and structure level are separate concepts. Live Draw v1 outputs Large-Dow and Mid-Dow structures only; it does not hard-map a timeframe to a Dow level.

TL is the primary draw object. CH, TL Zone, and CH Zone are subordinate to the selected TL.

See:

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

Video / OpenAI API / Ollama remain outside the active Live Draw path.

## Hard boundaries

NCA does not emit or act on Entry, SL, TP, RR, Lot, Long/Short, Order, Ticket, or any trading decision. NCA does not write new detector logic or rules back into NODA Engine.
