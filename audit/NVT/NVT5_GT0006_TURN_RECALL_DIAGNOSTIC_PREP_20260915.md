# NVT5 GT_0006 Turn Recall Diagnostic Preparation Audit

Date: 2026-09-15  
Branch: `feature/nvt-validation-v1`  
Status: PREPARED / RUN REQUIRED

## Trigger

GT_0006 (USDJPY H1, teacher video 2026-09-12 00:30:50–00:31:49) produced `ABSENT` in the teacher-anchor-window probe. The teacher visually treats the highlighted rebound point as a small-Dow high, while the current NCA candidate pool did not contain the corresponding teacher-like anchor pair.

## Audit question

Determine exactly where the recall loss occurs:

1. visually obvious local HIGH exists but is inside the production FALLING active leg;
2. HIGH becomes an active rising extreme but is not confirmed by the 38% closed-bar retracement rule;
3. confirmed HIGH pivots exist, but the FALLING candidate pair is rejected by price-order or CH geometry gates;
4. candidate actually exists and the prior probe/window hypothesis was wrong.

## Added research tooling

- `tools/nvt/diagnose_gt0006_turn_recall.py`
- `setup/RUN_NVT5_GT0006_TURN_DIAGNOSTIC.cmd`
- `docs/NVT/NVT_TURN_RECOGNITION_IMPROVEMENT_CANDIDATES_V01.md`

The diagnostic reuses production `detect_turns()` and `build_channel_candidates()` read-only. It does not alter their behavior.

## Output

`%APPDATA%\MetaQuotes\Terminal\Common\Files\noda_draw\nvt_output\GT_0006_TURN_RECALL_DIAGNOSTIC.json`

The output includes:
- H1 local highs in 2026-09-01 through 2026-09-11;
- production detector state at each local high;
- whether each high became a confirmed production HIGH pivot;
- 38% threshold context where applicable;
- small-Dow research label `LOW_HIGH_LOWER_LOW`;
- confirmed HIGH pairs in the teacher anchor windows;
- exact candidate-generator gate result;
- a primary diagnosis classification.

## Research-only local-high lens

The diagnostic uses simple L1/R1 and L2/R2 local extrema only as an observational lens. These are **not** proposed production pivots and do not write back to NCA.

## Production safety

No modifications were made to:
- production Normal Run;
- `tools/live_draw/turn_detector.py`;
- `tools/live_draw/geometry.py`;
- snapshots/state;
- `NCA_DRAW__` objects;
- trade state or order authority.

## Improvement hypotheses recorded

Priority order is documented as:
1. nested Micro-Dow layer;
2. confirmed + provisional pivot pools;
3. multi-scale turn recognition;
4. cluster-edge metadata;
5. wick-outlier tagging;
6. candidate identity/duplicate audit;
7. retracement-threshold sensitivity for diagnosis only, not blind tuning.

No hypothesis is FIXED or production-approved at this stage.
