# NVT6 Gate + Selector Research Audit — 2026-09-16

Status: RESEARCH ONLY

## Corrected process order

1. GT_0005 semantics are processed first.
   - Valid small-Dow trend line / turn line.
   - Can be drawn from valid highs, including a full small-Dow phase.
   - Steep angle; tends to become unnecessary quickly with time.
   - Intentionally not displayed to avoid line clutter.
   - Not an ownership rejection and not an invalid-line negative.
   - Exact anchors remain DRAFT and are deferred to later lifecycle/visibility quantification.
2. GT_0006 is the positive H1 descending-line selector case.
3. GT_0007 remains the timeframe-global H1 NO-LINE negative control.

## Ownership gate hypotheses

A. H4 + D1 direction consensus at teacher-decision cutoff.

B. H4 + D1 anchor ownership at teacher-decision cutoff, defined as H1 anchor1 price matching the latest same-side structural pivot price on both higher timeframes. Exact bar-time equality is not required because higher-timeframe bar opens differ.

C. A + B.

These are hypotheses only. One positive and one global negative control are insufficient for production promotion.

## Current observed evidence from NVT6 feature probe

- GT_0006: 13 latest-origin P38->MICRO candidates; all are FALLING.
- GT_0006: at cutoff, all 13 agree with both H4 and D1 direction and share the same H1 anchor1 price that is also the higher-timeframe latest same-side pivot price.
- GT_0007: 9 latest-origin P38->MICRO candidates; none satisfy both-H4+D1 direction consensus at cutoff, and none satisfy both-H4+D1 anchor ownership at cutoff.
- Therefore A, B, and C each separate the current GT_0006 positive case from the GT_0007 global negative control, but this remains research evidence rather than a fixed rule.

## Selector pre-ranking scope

After research Gate C, GT_0006 candidates are compared using peer-relative evidence only:

- gentle slope rank
- anchor2 recency rank
- anchor2 wick rank / wick fraction
- elapsed hours

No teacher-line winner is fixed yet.

Important guards:

- Recency is not equivalent to teacher cluster-right-edge.
- Wick evidence is a penalty/tag candidate, not a hard-delete rule.
- Exact GT_0006 anchors remain DRAFT.
- Cluster-right-edge requires a separate evidence-driven definition before final selector scoring.

## Production boundary

No production Normal Run code is modified.
No production 38% Turn Detector rule is modified.
No NCA_DRAW__ MT4 object is written or altered.
No trade authority is introduced.
