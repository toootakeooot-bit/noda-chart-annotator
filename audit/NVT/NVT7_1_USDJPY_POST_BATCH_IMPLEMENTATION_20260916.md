# NVT7.1 USDJPY Post-Batch Implementation Audit — 2026-09-16

Status: **IMPLEMENTED / RESEARCH ONLY / AWAITING HOST EXECUTION**

## Purpose

Apply the USDJPY historical user adjudication from `NVT8H_USDJPY_USER_ADJUDICATION_BATCH01.json` as a new research layer without mutating the already frozen NVT7 scoped beta.

## New research contracts

1. **TL_BREAK != DIRECTION_FLIP**
   - HIST03: a temporary H1 TL break does not establish an H1 downtrend by itself.
   - The adjudicated case had no meaningful lower-low update.
   - A small-Dow BR line may be drawn as an auxiliary line without flipping the parent H1 structure.

2. **REFERENCE retirement by structural subsumption, not recency**
   - HIST07: an old reference may eventually retire.
   - A newer line does not delete the old line merely because it is newer.
   - A broader/gentler valid line may outlive a steeper interim redraw.
   - `RETIRED_REFERENCE` is only a user-operational research candidate; it is not teacher-validated or frozen.

3. **Visibility and decision ownership are separate**
   - HIST08: H1/H4 lines may remain visible for context after their TLs are broken.
   - Primary judgment may escalate to D1 TL.
   - A new H1 descending TL is not required for the primary decision at that moment.

## Implementation

Added:

- `tools/nvt/build_nvt7_1_post_batch_candidate.py`
- `tools/nvt/run_nvt7_1_post_batch_regression.py`
- `setup/run_nvt7_1_usdjpy_post_batch.ps1`
- `setup/RUN_NVT7_1_USDJPY_POST_BATCH.cmd`

Host output directory:

`%APPDATA%\MetaQuotes\Terminal\Common\Files\noda_draw\nvt_output\nvt7_1_post_batch\`

Expected outputs:

- `NVT7_1_POST_BATCH_CANDIDATE.json`
- `NVT7_1_HISTORICAL_REGRESSION.json`
- `NVT7_1_POST_BATCH_HANDOFF.json`

## Regression scope

The regression checks that:

- the original frozen NVT7 scoped beta remains intact;
- HIST03 reproduces the adjudicated break-vs-direction behavior;
- HIST07 permits conditional retirement while forbidding newest-only deletion;
- HIST08 separates lower-TF line visibility from D1 decision ownership;
- HIST01/02/04/05/06 remain unadjudicated and are not silently relabelled;
- Production Normal Run and MT4 objects remain untouched.

## Interpretation guard

`PASS_CONTRACTS` means only that the research candidate reproduces the recorded user-operational contracts and preserves the original frozen scope. It is **not** strict NVT8 held-out validation, teacher validation, or Production promotion evidence.

## Production boundary

No changes to:

- Production Normal Run
- `tools/live_draw` production semantics
- production `NCA_DRAW__` objects
- trade execution authority

Production promotion remains prohibited before NVT9.
