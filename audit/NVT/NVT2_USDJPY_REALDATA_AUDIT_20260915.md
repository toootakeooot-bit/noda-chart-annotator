# NVT2 USDJPY Real-Data Audit — 2026-09-15

Status: **PASS**

Branch: `feature/nvt-validation-v1`

## Evidence received

User executed the revised NVT2 corpus runner after updating to the branch state that includes Ground Truth JSON validation and Python-owned teacher JSON parsing.

Observed successful gates:

- Ground Truth JSON validation: PASS
- Ground Truth cases: 7
- Required source/timeframe pairs: 5
- Required TFs: D1 / H1 / H4
- Optional TFs do not gate the run
- Candidate dump generation completed for all required pairs
- Final runner result: `NVT2 USDJPY CORPUS PASS`
- Generated required pairs: 5

Example final required pair shown in evidence:

- Source: `NVT_VIDEO_20260912`
- TF: H1
- cutoff: `2026-09-11T23:59:59`
- cases: `GT_0005,GT_0006`
- closed_bar_count: 2035
- confirmed_turn_count: 173
- candidate_count: 3364
- selected_large_candidate_id: `FALLING:2026-06-11T15:00:00:2026-09-02T04:00:00`
- selected_mid_candidate_id: `FALLING:2026-06-18T22:00:00:2026-09-02T04:00:00`

## Audit conclusion

NVT2 is accepted as PASS for the current USDJPY Ground Truth corpus.

This proves that the research pipeline can:

1. validate the Ground Truth corpus before execution,
2. derive only the Ground-Truth-required Source × TF pairs,
3. replay the available NVT history to provisional date cutoffs,
4. generate the candidate pools required for NVT3 comparison,
5. complete without modifying production Normal Run input/state/snapshot or `NCA_DRAW__` objects.

## Remaining limits

- Current cutoffs are still provisional date-level upper bounds.
- Exact teacher decision-bar cutoffs remain an NVT5 task.
- Current Ground Truth anchors are still DRAFT / partially UNKNOWN, so NVT3 may legitimately return `PENDING_GROUND_TRUTH` for dimensions that cannot yet be hard-scored.
- M15 deep history is not required by the current 7 Ground Truth cases and was therefore intentionally not used as a gate.

## Next gate

Proceed to NVT3 Teacher–NCA Diff using the 5 generated candidate pools and 7 Ground Truth cases.
