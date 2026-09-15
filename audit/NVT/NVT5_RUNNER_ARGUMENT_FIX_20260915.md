# NVT5 Runner Argument Fix Audit — 2026-09-15

## Status

FIXED

## Observed failure

User PC execution reached:

```text
NVT5 STEP -1: exact-cutoff + replay selftest
NVT5 SELFTEST PASS
NVT5 STEP 0: Ground Truth JSON validation
validate_ground_truth.py: error: unrecognized arguments: --symbol USDJPY
NVT5 FAIL: Ground Truth validation failed exit=2
```

## Root cause

`setup/run_nvt5_usdjpy_replays.ps1` passed `--symbol USDJPY` to `tools/nvt/validate_ground_truth.py`, but the validator CLI only defines:

```text
--ground-truth-dir
```

This was a runner/interface mismatch. It was not:

- a Ground Truth JSON failure;
- an NVT5 replay failure;
- an OHLC/history failure;
- a production NCA failure.

## Fix

Removed the unsupported `--symbol USDJPY` argument from the NVT5 validator invocation.

Ground Truth symbol filtering remains the responsibility of the later replay-plan builder, which explicitly accepts `--teacher-symbol USDJPY`.

## Follow-on audit

The remaining NVT5 runner calls were checked against their actual CLI contracts:

- `build_nvt5_replay_plan.py`: arguments match;
- `replay_to_time.py`: arguments match;
- `dump_candidates.py`: arguments match;
- `build_anchor_workbench.py`: arguments match.

Drawable Ground Truth cases such as GT_0001 contain Teacher objects with unknown anchors and are therefore eligible for Anchor Review Workbench generation. Explicit NO-LINE cases remain empty `teacher_objects` by design.

## Production impact

None.

The fix changes only the NVT research runner. No production Normal Run state/snapshot, `tools/live_draw/` semantics, MT4 `NCA_DRAW__` objects, or trade state is modified.
