# NVT6 Gate / Selector Current Result — 2026-09-16

Status: RESEARCH ONLY

## Evidence received

The current user-run outputs are consistent and pass their research guards:

- GT_0005_DISPLAY_SUPPRESSION_PRECHECK.json: PASS
- NVT6_OWNERSHIP_GATE_HYPOTHESES.json: research evidence generated
- GT_0006_SELECTOR_PRERANK.json: research pre-rank generated

## GT_0005 correction remains active

GT_0005 is a valid small-Dow turn line, not an ownership negative and not an invalid-candidate case.
It is intentionally not displayed because the line is steep / short-lived and because displaying every such line would create clutter.
Exact anchors remain DRAFT and are only required later for lifecycle / visibility quantification.

## Ownership gate result

For the currently tested H1 cases:

- GT_0006 positive case: 13/13 candidates pass A, B and C.
- GT_0007 timeframe-global NO-LINE control: 0/9 candidates pass A, B or C.

A = H4 + D1 direction consensus at teacher-decision cutoff.
B = anchor1 price ownership by latest same-side H4 + D1 pivots at cutoff.
C = A and B.

This is strong separation for the current pair, but it is not enough to fix a production ownership rule.

## GT_0006 pre-rank result

The same candidate is rank 1 for both gentle slope and anchor2 recency:

- anchor1: 2026-09-02 04:00 / 160.387
- anchor2: 2026-09-11 15:00 / 154.480
- gentle slope rank: 1
- recency rank: 1
- low-wick rank: 9 / 13

The maximum wick candidate is instead 2026-09-09 04:00 / 153.826 with wick fraction about 0.877. Therefore wick must remain contextual and must not be used as a hard deletion rule.

## Cluster-right-edge next step

Recency is not identical to teacher cluster-right-edge. A research-only sensitivity probe is added using data-driven anchor2 price-cluster thresholds derived from nearest-neighbor price distances. It does not fix a teacher cluster definition.

The current data imply the following threshold values:

- NN Q50: approximately 0.113
- NN Q75: approximately 0.175
- NN Q75 x2: approximately 0.350

Across these sensitivity variants, 2026-09-11 15:00 remains a right-edge candidate and is also gentle-slope rank 1. This makes it a strong cross-feature research lead, not a locked teacher anchor.

## Guard

No production NCA state, Normal Run logic, NCA_DRAW__ objects, MT4 objects or trade authority are modified in NVT6 research.
