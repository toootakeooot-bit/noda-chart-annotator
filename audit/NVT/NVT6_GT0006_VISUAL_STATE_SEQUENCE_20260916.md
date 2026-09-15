# NVT6 GT_0006 Visual State Sequence Audit — 2026-09-16

Status: RESEARCH ONLY / NO PRODUCTION WRITEBACK

## Trigger

The first GT_0006 visual-geometry pass reduced 13 Gate-C candidates to a three-candidate late gentle family using one MT4 tooltip sample from `Trendline 55257`. The next audit checked whether later samples from the same video were compatible with one fixed geometry.

## Direct video observations

Source: `分析共有_26-9-12.mp4`, GT_0006 interval 00:30:50-00:31:49.

Observed MT4 object name: `Trendline 55257`.

Samples recorded for research comparison:

- V1 ~00:31:12.38: status-bar time 2026-09-03 11:00, tooltip line value 159.560.
- V2 ~00:31:13.88: status-bar time 2026-09-04 02:00, tooltip line value 158.215.
- V3 ~00:31:23.50: status-bar time 2026-09-03 05:00, tooltip line value 158.650.
- V4 ~00:31:45.00: status-bar time 2026-09-04 16:00, tooltip line value 156.718.

## Candidate comparison

Using the existing Gate-C family with common candidate anchor1 `2026-09-02 04:00 / 160.387`:

- V1 fits the late gentle family and does not separate 2026-09-11 02:00 / 11:00 / 15:00 anchor2 alternatives.
- V3 is closest to the 2026-09-04 12:00 candidate (about 0.036 price error).
- V4 is closest to the 2026-09-04 15:00 candidate (about 0.029 price error).
- V2 does not tightly fit one fixed common-anchor1 Gate-C candidate and is treated as transient/edit-state or otherwise unresolved evidence.

No single fixed Gate-C geometry is expected to explain all four observations under the per-sample tolerances.

## Interpretation correction

GT_0006 must not be reduced to one static `Cluster Right Edge + Gentle + Recency` ranking event.

The video supports a stateful sequence in which the same MT4 object identity can be edited/re-anchored while the teacher compares valid structural alternatives. The research decomposition is therefore:

1. STRUCTURE / OWNERSHIP
2. CLUSTER-RIGHT-EDGE VALID ALTERNATIVES
3. OPTIONAL LATER-HIGH RE-ANCHOR
4. GENTLE-ANGLE PREFERENCE
5. WICK-NOISE CONTEXT TAG

NVT6 should own candidate validity, ownership and selector preference evidence. Same-object geometry replacement/update belongs to the NVT7 lifecycle model.

## Guards

- Do not lock GT_0006 exact anchors from V1 alone.
- Do not treat the same MT4 object name as proof of unchanged geometry.
- Do not turn transient drag/edit samples into hard Ground Truth.
- Do not modify Production Normal Run, production `tools/live_draw`, `NCA_DRAW__`, or the 38% production detector in NVT6.
- Production promotion remains blocked until locked Ground Truth and later NVT regression requirements are satisfied.
