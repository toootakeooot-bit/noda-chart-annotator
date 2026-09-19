# NVT9 09/19 Visibility Phase-1 Audit

Audit ID: ID10IQ200  
Date: 2026-09-19  
Scope: USDJPY# / 09-19 teacher evidence / H1-first visibility review

## Gate status

| Gate | Status | Result |
|---|---|---|
| V0 Baseline lock | PASS | Current Production behavior stays 16 rows per D1/H4/H1/M15. No writeback. |
| V1 NCA rationale mechanism | IMPLEMENTED | Existing draw-rationale tool explains line set, anchors, contacts and lifecycle role. |
| V2 Teacher registry | PASS | Frozen from corrected NVT8 09/19 held-out evidence. |
| V3 Teacher/NCA comparison | PASS_WITH_VISIBILITY_OPEN | Primary H1 Large TL/CH agree with teacher evidence; state coexistence is valid. Exact zone-edge visibility is not teacher-asserted. |
| V3.5 Cross-TF ownership | IMPLEMENTED_PENDING_LOCAL_MATRIX | Source TF may differ from structural owner TF; adjacent TFs must be compared before visibility reduction. |\n| V4 Visibility rule candidate | BLOCKED_PENDING_V3.5 | Prior H1 16->12 hypothesis remains only as a test candidate until ownership is classified. |
| V5 09/19 invariant regression | WAIT | Run after V3.5 ownership and revised V4 visibility rule. |
| V6 Preview snapshot | WAIT | Existing preview builder is retained but must wait for V3.5/V4. |
| V7 MT4 visual comparison | NOT_STARTED | Start only after V6 local output confirms expected counts. |

## Why H1 is the first visibility target

The 09/19 held-out teacher evidence requires the active H1 Large support TL, its channel, useful prior references, and coexistence of parent/local structures. It does not assert that every retained previous generation must show both zone edges.

The former visibility-only candidate is retained as a secondary experiment. Cross-TF ownership is now reviewed first; only if ownership does not explain the clutter should this minimal display reduction be evaluated:

- CURRENT LARGE/MID: TL + CH + both zone edges remain DRAW.
- PREVIOUS LARGE/MID: TL + CH remain REFERENCE.
- PREVIOUS LARGE/MID: TL_ZONE_EDGE + CH_ZONE_EDGE become SUPPRESSED in preview only.

Expected H1 count: 16 -> 12.

D1/H4/M15 remain 16 because the 09/19 teacher visibility evidence being used for this first rule is H1-specific.

## Safety boundary

This phase does not change Turn detection, candidate generation, selector semantics, lifecycle state, Production snapshot, Production Renderer, or existing NCA_DRAW__ objects.

A V6 preview PASS is not Production approval. The next gate is V7 visual comparison on MT4.
