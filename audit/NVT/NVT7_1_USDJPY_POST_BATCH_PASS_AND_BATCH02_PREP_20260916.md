# NVT7.1 USDJPY Post-Batch PASS / Batch02 Preparation — 2026-09-16

Status: **POST-BATCH CONTRACTS PASS / BATCH02 IMPLEMENTED / RESEARCH ONLY / AWAITING HOST EXECUTION**

## Observed host handoff result

User returned `NVT7_1_POST_BATCH_HANDOFF.json` with:

- schema: `nvt7.1-usdjpy-post-batch-handoff/0.1`
- status: `PASS_CONTRACTS`
- scope: `USDJPY_ONLY`
- evidence class: `USER_OPERATIONAL_EVIDENCE`
- `original_nvt7_scoped_beta_unchanged = true`
- all 12 regression contracts passed
- production writeback: false
- Normal Run modified: false
- MT4 object writeback: false

The PASS means the NVT7.1 research candidate reproduces the recorded HIST03/HIST07/HIST08 user adjudication without overwriting the frozen NVT7 beta and without silently relabeling HIST01/02/04/05/06. It is not strict NVT8 held-out validation and is not production readiness.

## New research contracts carried forward

1. `TL_BREAK != DIRECTION_FLIP`
   - HIST03 evidence.
   - A local H1 falling active leg does not override a still-useful rising parent H1 TL/CH by itself.
   - Small-Dow BR may be optional auxiliary structure without flipping parent direction.

2. `REFERENCE_RETIRE_BY_STRUCTURAL_SUBSUMPTION`
   - HIST07 evidence.
   - Reference retention is conditional, not permanent.
   - Newest-only deletion is forbidden.
   - A broader/gentler valid structural replacement may retire an older reference or outlive a steeper interim redraw.

3. `VISIBILITY != DECISION_OWNER`
   - HIST08 evidence.
   - Lower-TF lines may remain visible for context after losing primary decision authority.
   - Observed case escalates primary decision ownership to D1 after H1/H4 TL break.

## Still unresolved

- No objective numeric threshold is fixed for meaningful lower-low / direction-flip confirmation.
- No objective numeric threshold is fixed for structural subsumption or broad/gentle replacement.
- Decision-owner escalation is not generalized beyond the adjudicated HIST08 pattern.
- `RETIRED_REFERENCE` still lacks teacher-video validation.

## Batch02 implementation

Added a targeted historical review builder and host runner:

- `tools/nvt/build_nvt7_1_usdjpy_targeted_review.py`
- `setup/run_nvt7_1_usdjpy_targeted_review.ps1`
- `setup/RUN_NVT7_1_USDJPY_TARGETED_REVIEW.cmd`

Batch02 uses future-hidden daily USDJPY cutoffs and excludes the prior Batch01 cutoffs. It searches for three mechanical *review candidates* only:

- H1 FALLING active leg while H1 Large/Mid remain RISING (`BREAK_NOT_DIRECTION_FLIP_CANDIDATE`)
- sequential H1 Large/Mid candidate-ID change without direction change (`REFERENCE_REANCHOR_RETIRE_REVIEW_CANDIDATE`)
- H1 and H4 active legs FALLING while D1 Large remains RISING (`DECISION_OWNER_ESCALATION_CANDIDATE`)

These patterns are case surfacing heuristics, not labels or teacher answers. No numeric thresholds are invented. ChatGPT reviews first; the user adjudicates only ambiguous/high-impact cases.

Expected host output:

`%APPDATA%\MetaQuotes\Terminal\Common\Files\noda_draw\nvt_output\nvt7_1_targeted_usdjpy\NVT7_1_USDJPY_TARGETED_REVIEW_BATCH02.json`

## Guardrails

- Original NVT7 scoped beta remains frozen and unchanged.
- NVT7.1 remains a separate research candidate.
- No production `tools/live_draw` semantic changes.
- No `NCA_DRAW__` changes.
- No MT4 production drawing writeback.
- No trade authority.
- No NVT9 promotion claim.
