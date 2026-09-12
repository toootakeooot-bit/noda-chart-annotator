# NODA Chart Annotator — PDF-only Local Mode v0.5

Purpose: reproduce/annotate Teacher-drawn chart structures from the weekly chart material without using video and without OpenAI API calls.

## Scope
- Primary source: Teacher chart PDF / chart images.
- Secondary source: Chatwork `分析共有` post metadata.
- Rule context: current NODA R01–R20 + confirmed Selection semantics.
- Video: HOLD / not used.
- OpenAI API: HOLD / not used.
- No-chart week: `NO_CHART_WEEK` and clean PASS.
- Unknown teacher rationale: `UNKNOWN` / `VIDEO_RATIONALE_PENDING`; do not invent.

## Hard boundary
This project is separate from NODA Engine. It must not emit Entry/SL/TP/RR/Lot/Long/Short/Order/Ticket fields or trading actions.

## Local pipeline
Chatwork -> Archive -> Queue -> Package -> PDF-only Local Teacher Parser -> Teacher Observation -> existing P5-5 Parser/Comparator -> MT4 Bridge/Renderer.

The local parser uses Ollama + a vision-language model only on the PC. No cloud AI API is required.
