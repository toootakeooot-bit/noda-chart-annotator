# NVT6 Preflight Implementation Audit — 2026-09-15

Status: **IMPLEMENTED / RESEARCH ONLY / AWAITING HOST EXECUTION**

Repository: `toootakeooot-bit/noda-chart-annotator`  
Branch: `feature/nvt-validation-v1`

## Trigger

GT_0006 Micro-Dow prototype restored teacher-like H1 descending TL alternatives that were absent from the production Candidate Pool. The uploaded prototype result showed:

- production-confirmed anchor1 preserved;
- 12 strict Micro-Dow anchor2 alternatives from that confirmed origin;
- 48 falling Micro-Dow pairs overall;
- no production writeback.

NO-LINE evidence requires scope discipline:

- GT_0007 is the current strongest **timeframe-global H1 NO-LINE** control;
- GT_0005 is **structure-specific NO-LINE** evidence. It rejects the apparent structure being discussed, but GT_0006 shortly afterward contains a different valid H1 descending TL on the same source/cutoff.

Therefore GT_0005 must not be used as a blanket negative label for all H1 candidates at that cutoff. Its rejected structure must be identified separately.

A separate blocker also remains from GT_0003: repeated rows may share one `candidate_id` while CH anchor / structural metrics differ.

## Implemented research components

### Structure ownership preflight

- `docs/NVT/NVT6_STRUCTURE_OWNERSHIP_PREFLIGHT_V01.md`
- `tools/nvt/build_micro_dow_pool.py`
- `tools/nvt/evaluate_structure_ownership.py`
- `tools/nvt/run_structure_ownership_batch.py`
- `setup/run_nvt6_structure_ownership_preflight.ps1`
- `setup/RUN_NVT6_STRUCTURE_OWNERSHIP_PREFLIGHT.cmd`

Research provenance classes:

```text
P38_P38
P38_MICRO
MICRO_P38
MICRO_MICRO
```

The preflight deliberately outputs evidence rather than a production ownership decision.

### GT_0003 candidate identity audit

- `tools/nvt/audit_candidate_identity.py`
- `setup/run_nvt6_gt0003_candidate_identity_audit.ps1`
- `setup/RUN_NVT6_GT0003_CANDIDATE_IDENTITY_AUDIT.cmd`

Duplicate classes:

```text
SAME_TL_DIFFERENT_CH
SAME_GEOMETRY_DIFFERENT_CONTEXT_METRICS
EXACT_DUPLICATE_ROWS
```

### Combined host runner

- `setup/run_nvt6_preflight_all.ps1`
- `setup/RUN_NVT6_PREFLIGHT_ALL.cmd`

## Important implementation corrections

### Full-history production Pivot provenance

The generic Micro-Dow pool builder initially applied the research lookback before running the production 38% detector. That could have changed production-equivalent pivot state. It was corrected before host execution:

```text
full frozen history
 -> production detect_turns(38%)
 -> research lookback only for Micro-Dow/local-extrema pool
```

Thus production-confirmed pivot provenance is measured from the full frozen history.

### NO-LINE scope

The Ground Truth schema amendment draft was refined to distinguish:

```text
TIMEFRAME_GLOBAL
STRUCTURE_SPECIFIC
OBJECT_SPECIFIC
UNKNOWN
```

The current preflight evaluator treats GT_0007 as a global negative-control candidate and GT_0005 as structure-specific evidence requiring a rejected-structure target before candidate-level scoring.

## Expected host outputs

```text
nvt_output/nvt6_ownership/
  NVT_VIDEO_20260808_H1_MICRO_DOW_POOL.json
  NVT_VIDEO_20260912_H1_MICRO_DOW_POOL.json
  GT_0005_STRUCTURE_OWNERSHIP_EVIDENCE.json
  GT_0006_STRUCTURE_OWNERSHIP_EVIDENCE.json
  GT_0007_STRUCTURE_OWNERSHIP_EVIDENCE.json
  NVT6_STRUCTURE_OWNERSHIP_PREFLIGHT_SUMMARY.json

nvt_output/nvt6_identity/
  GT_0003_CANDIDATE_IDENTITY_AUDIT.json
```

## Required interpretation

A PASS from these runners means **reports were generated successfully**, not that an ownership rule or selector is validated.

The intended questions are:

1. Does GT_0006 retain `P38_MICRO` recall in the generic pool?
2. Does GT_0007 contain recognizable candidates despite timeframe-global teacher NO-LINE evidence?
3. Can the rejected structure in GT_0005 be identified separately from GT_0006's valid H1 structure?
4. What form of candidate identity collision exists in GT_0003?
5. Only after those answers may NVT6 Structure Selector beta scoring be designed.

## Production impact

None.

```text
production tools/live_draw semantics: unchanged
Normal Run: unchanged
NCA_DRAW__: unchanged
MT4 production objects: unchanged
trade authority: none
ChatGPT runtime dependency: none
TC dependency: none
NODA Engine writeback: none
```

## Next gate

Run `setup/RUN_NVT6_PREFLIGHT_ALL.cmd` on the host with existing NVT5 outputs. Review the resulting ownership summary and candidate-identity audit before implementing selector weights or production-like ownership rules.
