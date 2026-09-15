# GT_0006 Turn Recall Diagnostic Result — 2026-09-15

Status: **EVIDENCE CAPTURED / RESEARCH ONLY**

## Source

Input: `GT_0006_TURN_RECALL_DIAGNOSTIC.json`

Case: `GT_0006`, USDJPY H1, source `NVT_VIDEO_20260912`.

## Key result

The diagnostic supports a **turn/structure-scale recall gap**, not a selector error and not a downstream Candidate Generator gate error.

Observed in 2026-09-01 through 2026-09-11 H1:

- local highs found: 46
- production confirmed HIGH pivots: 1
- local highs classified as inside the production FALLING leg: 39
- active highs replaced before confirmation: 2
- local highs not equal to the active rising extreme: 4
- confirmed HIGH pivots in teacher anchor1 window: 1
- confirmed HIGH pivots in teacher anchor2 window: 0
- confirmed anchor-pair gate rows: 0
- teacher-like micro-Dow pairs: 96
- primary diagnosis: `TURN_OR_SCALE_RECALL_GAP_LIKELY`

Therefore the current production Candidate Generator never receives a second confirmed HIGH from the teacher anchor2 window. The teacher-like pair cannot reach Selector because its second anchor is absent upstream.

## Important interpretation

This does **not** mean that the visible rebound highs are not highs in ordinary small-Dow terms. It means production Turn Detector v1 represents the entire move as one larger active FALLING leg until its 38% close-retracement confirmation condition is met. Nested rebound highs are consequently suppressed as independent confirmed pivots.

The strongest observed pattern is:

`LOW -> rebound HIGH -> LOWER LOW`

Many such rebound highs exist while production remains in the same FALLING leg.

## Decision

Do not tune the Selector to fix GT_0006. Do not lower the production 38% constant merely to make this case pass.

Proceed with a research-only nested `MICRO_DOW` prototype that:

1. keeps production `CONFIRMED_38` pivots unchanged;
2. separately records structurally validated small-Dow rebound highs/lows;
3. preserves multiple anchor alternatives;
4. does not auto-promote or render them;
5. must later be protected by structure-ownership / NO-LINE gates, especially GT_0005 and GT_0007.

## Additional improvement directions

- separate confirmed and provisional/micro pivot pools;
- explicit multi-scale parent/child swing ownership;
- cluster-edge metadata rather than collapsing nearby anchors immediately;
- wick-outlier tagging rather than global wick deletion;
- candidate identity/deduplication audit before NVT6 scoring;
- threshold sensitivity only as a diagnostic matrix, not a fitting mechanism.

## Production impact

None.

- `tools/live_draw/`: unchanged
- Normal Run: unchanged
- `NCA_DRAW__`: unchanged
- MT4 objects: unchanged
- trade authority: none
