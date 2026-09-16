# NVT8-H USDJPY Historical Human-Adjudicated Validation

Status: **IMPLEMENTED / RESEARCH ONLY / NOT STRICT NVT8 HELD-OUT**
Date: 2026-09-16

## Purpose

Provide a supplemental USDJPY historical validation path when no teacher video/answer exists. ChatGPT performs the mechanical review first and surfaces only ambiguous/high-impact items for user adjudication.

## Method

- USDJPY only.
- Uses research-only deep history in `noda_draw/nvt_input`.
- Selects deterministic weekly H1 cutoffs outside the known 2026-08-01..2026-09-15 development-video window.
- Includes only bars at or before each cutoff; future bars are excluded.
- Packages D1/H4/H1/M15 chart windows plus production-baseline detector/selector summaries.
- Default first batch: 8 cases.
- User answer is intentionally absent; ChatGPT reviews first.

## Review protocol

1. Upload `NVT8H_USDJPY_REVIEW_BUNDLE.json` to ChatGPT.
2. ChatGPT renders/inspects the future-hidden cases and applies current NVT6/NVT7 research semantics.
3. ChatGPT asks the user only about cases/fields that remain ambiguous or materially affect the conclusion.
4. Record the judgment before any rule tuning.
5. Aggregate failure layers only after the batch is adjudicated.

## Boundary

This does **not** replace strict NVT8 independent teacher-video validation because there is no external teacher Ground Truth for these historical cases. It is supplemental operational/human-adjudicated validation.

No production Normal Run, `tools/live_draw` semantics, `NCA_DRAW__`, MT4 objects, or trade state are modified.
