# NVT7 Scoped Beta Freeze — 2026-09-16

Status: **IMPLEMENTED / RESEARCH ONLY / AWAITING HOST EXECUTION**

## Why the freeze model was changed

NVT7-1 through NVT7-4 passed the development-case lifecycle contracts, but the beta candidate still listed four unresolved items:

1. exact market-time sequence for GT_0006 re-anchor states;
2. objective threshold for GT_0005 short-lived/display suppression;
3. explicit RETIRED/DELETE transition evidence;
4. exact anchor locks for DRAFT cases where still pending.

These items do not all need to be invented or solved before a lifecycle beta can be validated. The correct research response is to freeze only the subset actually supported by evidence and to keep unsupported transitions/triggers explicitly outside the beta scope.

## Frozen NVT7 scope candidate

Market lifecycle states:

- `CURRENT_ACTIVE`
- `REFERENCE_RETAINED`
- `VALID_SUPPRESSED`
- `REANCHORED_CURRENT`

Observation-only filter state:

- `EDIT_TRANSIENT`

Frozen market-time transitions:

- GT_0002 `UPDATE_AND_KEEP_REFERENCE`
- GT_0004 `RESTORE_PERSISTENT_REFERENCE`

Frozen semantic guards:

- validity and visibility are separate;
- updating current geometry does not delete an older useful reference by default;
- newest geometry is not automatically the preferred monitoring reference;
- transient video drag/edit states are excluded from stable market-time lifecycle evidence;
- same MT4 object name does not imply immutable geometry.

## Explicitly deferred / not invented

- GT_0005 numeric automatic suppression threshold;
- GT_0006 market-time re-anchor order inferred from video drag/edit order;
- RETIRED/DELETE states or transitions without teacher evidence;
- exact geometric anchor locking where lifecycle semantics do not depend on it.

This does **not** waive the NVT9 promotion policy. Behavior-specific REVIEWED/LOCKED Ground Truth, NVT8 held-out validation, Normal Run regression, and MT4 verification remain required before production promotion.

## Implementation

Added:

- `tools/nvt/build_nvt7_scoped_freeze.py`
- `tools/nvt/run_nvt7_frozen_scope_regression.py`
- `setup/run_nvt7_scoped_freeze.ps1`
- `setup/run_nvt7_frozen_scope_regression.ps1`

Updated:

- `setup/NVT7_PIPELINE.json` to v0.3

The same one-click user entry point remains unchanged.

## Expected outputs

- `nvt7_lifecycle/NVT7_LIFECYCLE_SCOPED_BETA.json`
- `nvt7_lifecycle/NVT7_FROZEN_SCOPE_REGRESSION.json`

If NVT7-6 passes, only the frozen scoped lifecycle rules become ready for NVT8 held-out validation. Production remains unchanged.
