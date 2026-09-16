# NVT7 Sequential Regression / Beta Candidate Implementation — 2026-09-16

Status: **IMPLEMENTED / RESEARCH ONLY / AWAITING HOST EXECUTION**

## Input evidence

The NVT7 handoff bundle generated at host HEAD `7fc3c9a` reported:

- NVT7-1-2 stage PASS_GENERATED;
- all lifecycle preflight checks PASS;
- GT_0002 current + retained reference evidence present;
- GT_0004 persistent original reference evidence present;
- GT_0005 valid-but-display-suppressed semantics present;
- GT_0006 stable/transient visual states separated;
- production writeback false;
- Normal Run modified false;
- MT4 object writeback false.

## Added NVT7-3

`tools/nvt/run_nvt7_sequential_regression.py`

Checks evidence-derived lifecycle contracts for GT_0002 / GT_0004 / GT_0005 / GT_0006.

Core guards:

- current update must not automatically delete a still-useful reference;
- newest geometry is not automatically preferred over a persistent monitoring reference;
- display suppression does not invalidate a structurally valid line;
- GT_0006 transient edit evidence is excluded from stable market-time lifecycle training;
- GT_0006 video-edit order is not promoted to market-time transition order.

Output:

`nvt_output/nvt7_lifecycle/NVT7_SEQUENTIAL_REGRESSION.json`

## Added NVT7-4

`tools/nvt/build_nvt7_beta_candidate.py`

Builds a research lifecycle beta candidate only when NVT7-3 passes.

Candidate states:

- CURRENT_ACTIVE
- REFERENCE_RETAINED
- VALID_SUPPRESSED
- EDIT_TRANSIENT
- REANCHORED_CURRENT

The beta candidate is intentionally **not frozen** while unresolved evidence remains, including:

- exact market-time sequence for GT_0006 re-anchor states;
- objective threshold for GT_0005 short-lived/display suppression;
- explicit RETIRED/DELETE transition evidence;
- exact anchor locks for remaining DRAFT cases.

Output:

`nvt_output/nvt7_lifecycle/NVT7_LIFECYCLE_BETA_CANDIDATE.json`

## One-click integration

`setup/NVT7_PIPELINE.json` upgraded to schema `nvt7-pipeline/0.2`.

The same user entry point now runs:

1. NVT7-1-2 preflight + event/state graph
2. NVT7-3 sequential regression
3. NVT7-4 beta candidate build
4. bundle generation

The user still uploads only `NVT7_HANDOFF_BUNDLE.json`.

## Production protection

No Production Normal Run file or semantics were changed.
No `tools/live_draw/` file was changed.
No `NCA_DRAW__` object behavior was changed.
No MT4 object writeback was added.
No trade authority was added.

NVT0-NVT8 remain research/validation only; production promotion remains NVT9-only.
