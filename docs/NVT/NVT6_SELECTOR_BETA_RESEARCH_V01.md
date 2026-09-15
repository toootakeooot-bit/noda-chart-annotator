# NVT6 Selector Beta Research v0.1

Status: **RESEARCH ONLY / NOT PRODUCTION FIXED**

## Purpose

Define the current research sequence for H1 teacher-like line selection without modifying Production Normal Run, production Turn Detector, `NCA_DRAW__`, MT4 objects, or trade authority.

## Processing order

1. Candidate recall
   - Preserve the existing 38% confirmed structure.
   - Add Micro-Dow candidates only in the NVT research path.

2. GT_0005 visibility/lifecycle guard
   - A valid small-Dow turn line may be intentionally hidden.
   - Hidden does not mean invalid.
   - Hidden does not mean ownership rejection.
   - Steep / short-lived lines may be suppressed to avoid display clutter.

3. H1 ownership-gate research
   - Gate A: H4 + D1 direction consensus at teacher-decision cutoff.
   - Gate B: H1 anchor1 price owned by latest same-side H4 + D1 structural pivots at cutoff.
   - Gate C: A and B.
   - Current GT_0006 / GT_0007 separation is strong but insufficient to fix a production rule.

4. Cluster-right-edge research
   - Anchor2 recency is not the same as cluster-right-edge.
   - Probe price clusters using data-driven nearest-neighbor threshold sensitivity.
   - Define cluster right edge as the latest anchor2 time inside that price cluster for research only.
   - Do not fix the cluster threshold until visual anchors are confirmed across multiple cases.

5. Selector preference research
   - Prefer teacher-supported gentle-angle evidence only after ownership is established.
   - Treat wick outlier evidence as a contextual penalty/tag, never a universal hard deletion rule.
   - Current GT_0006 cross-feature lead must remain DRAFT until exact visual anchors are checked.

## Current GT_0006 lead logic

A candidate may become a research lead when it:

- survives Ownership Gate C;
- is a right-edge candidate under all tested cluster-threshold sensitivity variants; and
- is also on the gentle-slope + recency Pareto front.

This is not a production score and does not lock the teacher line.

## Regression guards

- GT_0005 must remain a valid-but-display-suppressed example.
- GT_0007 must remain a timeframe-global H1 NO-LINE control.
- GT_0003 forbids turning one large wick example into a universal wick-deletion rule.
- GT_0001 independently supports a rightmost-cluster-edge selection concept, but exact anchors remain DRAFT.
- Exact-anchor DRAFT cases must not be promoted to hard regression acceptance until LOCKED.

## Production boundary

NVT0–NVT8 remain research/validation only. Production promotion is deferred to NVT9 after held-out validation, regression against the production baseline, and actual MT4 visual verification.
