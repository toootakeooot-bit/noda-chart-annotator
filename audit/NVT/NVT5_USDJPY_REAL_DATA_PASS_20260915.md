# NVT5 USDJPY Real-Data PASS — 2026-09-15

Status: **PASS**

## Scope

This audit records user-observed execution evidence for the NVT5 USDJPY time-frozen replay on branch `feature/nvt-validation-v1`.

NVT5 remains research-only and does not modify production Normal Run state/snapshot, production `tools/live_draw/` semantics, MT4 `NCA_DRAW__` objects, or trade state.

## Observed execution result

The user-provided terminal evidence reached:

```text
NVT5 USDJPY TIME-FROZEN REPLAY PASS
Resolved replay pairs: 5
NVT5 USDJPY REPLAYS PASS
```

All required replay pairs therefore completed the NVT5 runner.

## Exact-cutoff behavior observed

The run resolved pair-specific cutoffs from actual XM closed-bar history. Examples visible in the execution evidence include:

```text
NVT_VIDEO_20260830 H4 -> 2026-08-28T20:00:00
NVT_VIDEO_20260905 D1 -> 2026-09-04T00:00:00
NVT_VIDEO_20260912 H1 -> 2026-09-11T23:00:00
```

The 2026-09-12 H1 replay reported:

```text
frozen_bar_count = 2035
excluded_future_bar_count = 37
look_ahead_guard = PASS
```

The 2026-09-05 D1 replay evidence also reported `look_ahead_guard = PASS`.

## Candidate/workbench evidence observed

For `NVT_VIDEO_20260905 / D1`:

```text
candidate_count = 7315
workbench GT_0004 = PASS
expected_no_line = false
teacher_object_count = 1
```

For `NVT_VIDEO_20260912 / H1`:

```text
candidate_count = 3364
workbench GT_0005 = PASS
expected_no_line = true
teacher_object_count = 0

workbench GT_0006 = PASS
expected_no_line = false
teacher_object_count = 1
```

This confirms that the workbench preserves the distinction between explicit NO-LINE evidence and drawable Teacher-object review cases.

## Gate result

NVT5 machine processing is accepted as PASS for the initial 7-case USDJPY corpus:

```text
required replay pairs resolved from actual broker OHLC: PASS
look-ahead guard observed: PASS
frozen candidate pools generated: PASS
anchor-review workbenches generated: PASS
NO-LINE cases preserved: PASS
production writeback: NONE
```

## Remaining work before NVT6

NVT5 does **not** itself lock Teacher anchors. The remaining drawable cases are:

```text
GT_0001
GT_0002
GT_0003
GT_0004
GT_0006
```

Their anchor evidence must be reconciled against source-video frames and frozen OHLC/candidate workbenches before any Selector rule is changed.

A portable review-bundle exporter is provided so the generated local NVT5 evidence can be reviewed without manually collecting many separate JSON files.
