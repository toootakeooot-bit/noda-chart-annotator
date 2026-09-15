# NVT6 GT_0005 Semantic Correction — 2026-09-16

Status: **RESEARCH ONLY — CORRECTION FIXED FOR NVT6 ORDERING**

Production `tools/live_draw/`, Normal Run, `NCA_DRAW__`, MT4 objects, NODA Engine, trade state: **UNCHANGED**.

## Corrected source interpretation

Case: `GT_0005`  
Video: `分析共有_26-9-12.mp4`  
Window: `00:29:48-00:30:29`

The discussed line is:

- a valid small-Dow TL;
- called a turn line by the teacher;
- drawable from valid highs;
- also drawable during a full small-Dow phase;
- geometrically steep;
- short-lived in practical usefulness because time passage makes it unnecessary quickly;
- intentionally not displayed in the shown depiction because drawing every such valid short-lived line would create excessive line clutter.

Therefore GT_0005 is **not**:

- an invalid-line case;
- a structure-ownership rejection;
- a timeframe-global NO-LINE case;
- evidence that the candidate should be absent from Candidate Pool.

It is a **valid-but-display-suppressed turn-line case**.

## NVT6 ordering consequence

GT_0005 must be processed before GT_0006 so its semantics are established first:

```text
GT_0005
  valid small-Dow turn line
  -> candidate validity preserved
  -> display suppression / short lifetime recognized
  -> DO NOT label as ownership negative
        |
        v
GT_0006
  ownership / candidate selection research
  -> cluster-edge / gentle-slope / wick evaluation
```

This ordering prevents the research pipeline from teaching NVT6 that a valid small-Dow line is structurally invalid merely because the teacher chose not to display it.

## Responsibility-layer interpretation

GT_0005 spans two responsibilities:

1. **Candidate / structure validity** — line is valid and may exist in the candidate set.
2. **Visibility / lifecycle policy** — line may be intentionally omitted because it is steep, short-lived, and contributes to clutter.

The second responsibility is closer to NVT7 Lifecycle / visibility policy, but its semantic classification must be fixed before GT_0006 NVT6 selector work so it does not contaminate ownership training.

## Ground Truth handling

`GT_0005.json` is corrected to remove the prior `expected_no_line` interpretation and records:

- `teacher_term=TURN_LINE`
- `structure_class=SMALL_DOW_TL`
- `candidate_valid=true`
- `geometry_character=STEEP_ANGLE`
- `lifecycle_character=SHORT_LIVED_BECOMES_UNNECESSARY_WITH_TIME`
- `display_policy=SUPPRESS_TO_AVOID_LINE_CLUTTER`
- `ownership_rejection=false`
- `invalid_line=false`

Exact anchors remain DRAFT and may be identified later for explicit lifetime / visibility scoring.

## Code changes

Research-only evaluators are revised so that GT_0005 yields:

`VALID_LINE_DISPLAY_SUPPRESSED_NOT_OWNERSHIP_NEGATIVE`

and the batch case order is explicitly:

`GT_0005 -> GT_0006 -> GT_0007`

GT_0007 remains the timeframe-global H1 NO-LINE negative control for ownership research.

## Gate state

```text
GT_0005 semantic classification: CORRECTED
GT_0005 candidate validity: VALID BY SOURCE INTERPRETATION
GT_0005 display policy: SUPPRESSED IN REFERENCE
GT_0005 ownership-negative use: PROHIBITED
GT_0006 selector research: MAY CONTINUE AFTER GT_0005 CLASSIFICATION
GT_0007 ownership negative control: RETAINED
Production writeback: NONE
```
