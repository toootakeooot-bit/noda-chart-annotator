# NVT9 09/19 Cross-TF Ownership Gate Adjustment

Audit ID: ID10IQ200  
Date: 2026-09-19

## Finding

The 09/19 visual review raises a higher-priority issue than simple object-count reduction: the timeframe that detects a line may not be the semantic timeframe to which the teacher assigns that structure.

The existing selector explicitly states that it has no timeframe-to-Dow mapping. Therefore a line selected as LARGE_DOW inside H4 is still H4-local in the current data model even if its geometry corresponds to a teacher D1 structural TL.

This is a model-identity issue, not merely renderer clutter.

## Existing evidence that supports separation

NVT7.1 already preserves a guardrail that line visibility must not be equated with decision ownership, and contains a case where prior lower-timeframe lines remain visible while primary decision ownership escalates to D1.

Therefore the new cross-TF structural-owner dimension can be added without overturning that principle.

## Gate decision

PAUSE the prior V4 visibility-only path.

The 16 -> 12 H1 candidate is retained as an experimental hypothesis but must not be promoted or visually tested as the primary solution until V3.5 ownership classification is completed.

## New required classification

For every current line family, record:

- source_tf
- structural_owner_tf
- same_family_parent_id if any
- relation: SAME_FAMILY / REFINED_PARENT / DISTINCT_LOCAL / AMBIGUOUS
- display recommendation: DRAW / REFERENCE / SUPPRESSED
- evidence and reason code

## 09/19 current hypothesis

User visual observation suggests:

- H4 NCA primary TL ~= teacher D1 TL
- H1 NCA primary TL ~= teacher H4 TL
- M15 NCA primary TL ~= teacher H1 TL

This is accepted as a research hypothesis, not yet as a production rule.

## Production safety

No Production Normal Run, selector, lifecycle, snapshot, Renderer, or NCA_DRAW__ behavior is modified by this gate adjustment.
