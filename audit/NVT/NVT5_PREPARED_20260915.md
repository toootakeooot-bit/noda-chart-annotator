# NVT5 Time-Frozen Replay — Preparation Audit 2026-09-15

Status: **TOOLING PREPARED / REAL XM RUN PENDING**

## 1. Trigger

NVT3 completed on real USDJPY research data with:

```text
report_count = 7
PENDING_GROUND_TRUTH = 5
NO_LINE_MISMATCH = 2
waiting_cases = 0
```

The next requirement is to tighten provisional source-date cutoffs and prepare the five drawable/pending cases for exact anchor review without look-ahead.

## 2. Fixed NVT5 method

Created:

```text
docs/NVT/NVT5_TIME_FROZEN_REPLAY_V1.md
```

Key method:

```text
weekend source
 -> expected Friday market date from manifest
 -> actual XM NVT deep-history CSV
 -> latest exported closed-bar timestamp on that exact broker date
 -> exact cutoff
 -> freeze all bars <= cutoff
 -> exclude every future bar
```

The video playback clock is not treated as a market clock.

## 3. Exact-cutoff resolver

Created:

```text
tools/nvt/build_nvt5_replay_plan.py
```

Outputs:

```text
NVT5_REPLAY_PLAN.tsv
NVT5_RESOLVED_CUTOFFS.json
```

Hard behavior:

- exact broker date must exist in the relevant TF CSV;
- no silent fallback to an earlier date;
- required pairs are derived from Ground Truth;
- production Normal Run inputs are not used.

## 4. Batch replay runner

Created:

```text
setup/run_nvt5_usdjpy_replays.ps1
setup/RUN_NVT5_USDJPY_REPLAYS.cmd
```

The runner performs:

```text
selftest
 -> Ground Truth syntax validation
 -> exact cutoff resolution
 -> pair-level Time-Frozen Replay
 -> exact-cutoff Candidate Dump
 -> per-case Anchor Review Workbench
 -> research summary
```

## 5. Selftest extension

Updated:

```text
tests/selftest_nvt5.py
```

The selftest now verifies both:

- exact cutoff derivation from a target market date with multiple same-day bars;
- replay look-ahead exclusion and writeback guards.

Expected synthetic result includes:

```text
exact_cutoff = 2026-01-03T02:00:00
frozen_bar_count = 5
excluded_future_bar_count = 1
look_ahead_guard = PASS
```

## 6. Anchor Review Workbench

Created:

```text
tools/nvt/build_anchor_workbench.py
```

Purpose: reduce manual review load without silently choosing Teacher anchors.

For each Teacher object, the workbench preserves candidates from multiple neutral review views:

```text
BASELINE_SELECTED
LONG_STRUCTURE_SPAN
HIGH_CONTACT_QUALITY
GENTLE_SLOPE
RECENT_ANCHOR2
UNBROKEN_CLOSE_EVIDENCE
```

The workbench explicitly does **not**:

- choose the Teacher match;
- modify Ground Truth;
- modify the NCA selector;
- promote any NVT rule to production.

For NO-LINE cases it records the NCA-selected candidate IDs only as mismatch evidence and does not reinterpret them as Teacher objects.

## 7. Production protection

No change was made to:

```text
tools/live_draw/
Normal Run semantics
production snapshot/state
MT4 NCA_DRAW__ ownership
trade authority
```

NVT5 outputs remain under NVT research paths.

## 8. Next real-data gate

User PC action required:

```text
RUN_NVT5_USDJPY_REPLAYS.cmd
```

Expected final gate:

```text
NVT5 SELFTEST PASS
NVT GROUND TRUTH VALIDATION PASS
NVT5 USDJPY TIME-FROZEN REPLAY PASS
Resolved replay pairs: 5
```

After this run, inspect:

```text
NVT5_RESOLVED_CUTOFFS.json
NVT5_USDJPY_REPLAY_SUMMARY.json
nvt5_replay/<source>/workbench_GT_*.json
```

Only then should exact Ground Truth cutoffs and Teacher anchors be amended/audited.

## 9. Audit conclusion

```text
NVT5 method: FIXED
NVT5 tooling: PREPARED
REAL XM exact-cutoff run: PENDING
Teacher anchors: NOT GUESSED
NVT6 selector modification: NOT STARTED
Production NCA modification: NONE
```
