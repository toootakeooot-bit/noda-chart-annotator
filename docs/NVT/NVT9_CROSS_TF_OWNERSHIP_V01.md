# NVT9 Cross-Timeframe Ownership Candidate V0.1

Audit ID: ID10IQ200  
Date: 2026-09-19  
Status: RESEARCH ONLY / NO PRODUCTION WRITEBACK

## Problem

The current Normal Run assigns semantic identity from the timeframe used to detect a line:

- D1 input -> D1 line
- H4 input -> H4 line
- H1 input -> H1 line
- M15 input -> M15 line

Teacher-chart review indicates this mapping can be too literal. A line detected from a lower-resolution source may represent the same broader structural line that the teacher treats as belonging to the next higher timeframe.

Observed 09/19 review hypothesis:

- NCA H4 TL may correspond to teacher D1 TL.
- NCA H1 TL may correspond to teacher H4 TL.
- NCA M15 TL may correspond to teacher H1 TL.

This MUST NOT be converted into a fixed one-step shift. Some H4 lines are genuinely H4-owned; some H1 lines are genuinely H1-owned.

## New dimensions

Each line family must be able to carry independent dimensions:

- source_tf: timeframe whose bars produced the geometry.
- structural_owner_tf: timeframe-scale structure the line represents.
- display_tf: chart timeframe where the object is currently shown.
- decision_owner_tf: timeframe whose structure currently has primary decision authority.

Do not infer equality among these fields.

## Core rule candidate

A lower-timeframe line may be promoted into the same cross-TF family as a parent-timeframe line only when the evidence supports structural equivalence.

Candidate evidence dimensions:

1. Direction agreement.
2. Common market swing / parent-leg correspondence.
3. Geometry agreement over a common comparison window, not merely one crossing point.
4. Compatible TL/CH relationship.
5. Parent structure remains valid under closed-bar break semantics.
6. Lower-timeframe candidate adds resolution rather than defining a distinct local structure.

If equivalence is established, structural_owner_tf is the HIGHEST timeframe represented in that family.

If equivalence is not established, structural_owner_tf remains source_tf.

## Explicitly forbidden rule

Do NOT implement:

H4 -> D1 always
H1 -> H4 always
M15 -> H1 always

The relation is conditional and case-dependent.

## Family examples

Example A:
- source_tf=H4
- structural_owner_tf=D1
- display_tf=H4
- role=REFERENCE_OR_REFINED_GEOMETRY

Example B:
- source_tf=H1
- structural_owner_tf=H1
- display_tf=H1
- role=LOCAL_STRUCTURE

Both are valid outcomes.

## Visibility interaction

Visibility must be decided AFTER cross-TF ownership.

A lower-TF line that duplicates a parent-owned family may be:

- DRAW if it materially improves geometry at that chart scale;
- REFERENCE if useful context remains;
- SUPPRESSED if visually redundant.

Suppression must not delete the underlying structure/lifecycle state.

## Decision ownership interaction

Existing NVT7.1 evidence already separates visibility from decision ownership. A lower-TF line can remain visible even after primary decision ownership escalates to D1. Cross-TF structural ownership therefore must also remain a separate dimension from decision_owner_tf.

## 09/19 gate change

The previous H1 visibility-only candidate (16 -> 12 by suppressing PREVIOUS zone edges) remains a test hypothesis but is no longer the next gate.

New order:

V0 baseline
V1 draw rationale
V2 teacher registry
V3 teacher/NCA comparison
V3.5 cross-TF family/ownership classification
V4 visibility rule derived after ownership
V5 regression
V6 preview
V7 MT4 comparison
V8 production promotion
V9 audit/reason logging

## Threshold policy

No numeric similarity threshold is frozen in V0.1.

Do not invent a slope, pip-distance, ATR-distance, or anchor-time tolerance from the 09/19 case alone. Collect teacher-labeled same-family and different-family examples first, then derive a robust tolerance or a non-numeric structural criterion.

## 09/19 questions to resolve

For each current NCA TL/CH family:

- Is NCA D1 same-family as teacher D1?
- Is NCA H4 same-family as teacher D1, teacher H4, or neither?
- Is NCA H1 same-family as teacher H4, teacher H1, or neither?
- Is NCA M15 same-family as teacher H1, teacher M15, or neither?
- Which lower-TF lines are refined representations of a parent structure?
- Which are independent local structures?

Only after this classification should visibility counts be reduced.
