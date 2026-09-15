# NVT3 USDJPY Real-Data Result — 2026-09-15

Status: **PASS AS RESEARCH RUN / DIFFERENCES FOUND**

## 1. Scope

Branch: `feature/nvt-validation-v1`

Input:
- NVT2 real-data candidate dumps for the 5 Ground-Truth-required source/timeframe pairs
- Ground Truth cases `GT_0001` through `GT_0007`
- broker data symbol `USDJPY#`

Production NCA state, snapshots, MT4 `NCA_DRAW__` objects, and `tools/live_draw/` were not modified.

## 2. Run result

NVT3 completed normally.

```text
report_count: 7
status_counts:
  PENDING_GROUND_TRUTH: 5
  FAIL: 2

failure_class_counts:
  GROUND_TRUTH_ANCHORS_PENDING: 5
  NO_LINE_MISMATCH: 2

Generated reports: 7
Waiting cases: 0
```

No runner/tool/JSON error occurred.

## 3. Interpretation

### 3.1 Five PENDING cases

Five cases remain `PENDING_GROUND_TRUTH` because the exact Teacher anchor bar timestamps/prices have not yet been locked.

These cases must not be treated as PASS or FAIL for Candidate/Anchor/Selector quality until NVT5 time-frozen replay and exact anchor annotation are completed.

### 3.2 Two hard mismatches

The two hard mismatches are the explicit H1 NO-LINE cases:

- `GT_0005` — source `NVT_VIDEO_20260912`, H1
- `GT_0007` — source `NVT_VIDEO_20260808`, H1

Both Ground Truth cases intentionally have zero `teacher_objects` and encode that the Teacher does not want an H1 trend line for the shown structural scale.

Current NCA nevertheless selected at least one Large/Mid candidate for the corresponding H1 candidate dump; therefore NVT3 correctly classified both as:

```text
NO_LINE_MISMATCH
```

This is research evidence of a current NCA responsibility/selection gap, not a runner failure.

## 4. First architectural conclusion

The first confirmed Teacher/NCA difference is not yet an anchor-geometry difference.

It is:

```text
STRUCTURE OWNERSHIP / NO-LINE DECISION
```

Current NCA generally assumes that a valid candidate set should yield Large/Mid line output. Teacher evidence shows that a visible shape can belong to a different structural scale, making zero line output on the displayed timeframe the correct result.

Do not patch this directly into production yet.

## 5. Next gate

Next work should proceed in this order:

1. NVT5: tighten provisional source-date cutoffs to exact time-frozen market cutoffs.
2. Lock exact Teacher anchor bars for the five pending cases where evidence permits.
3. Re-run NVT2/NVT3 with locked anchors.
4. Quantify Candidate Present / Anchor Match / Selector Match for those cases.
5. Only after those results decide whether NVT6 needs:
   - structure-ownership / NO-LINE gate,
   - selector scoring changes,
   - candidate-generation changes,
   - or multiple layers.

## 6. Production boundary

Per NVT Integration Policy v1:

- NVT0–NVT8 do not modify production NCA behavior.
- Existing Normal Run remains the baseline and rollback reference.
- NVT9 is the first allowed production-promotion stage.
