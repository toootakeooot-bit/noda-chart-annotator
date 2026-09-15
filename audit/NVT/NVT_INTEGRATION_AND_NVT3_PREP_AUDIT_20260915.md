# NVT Integration / NVT3 Preparation Audit — 2026-09-15

Status: **PASS FOR CONTINUED NVT DEVELOPMENT / PRODUCTION UNCHANGED**

Repository: `toootakeooot-bit/noda-chart-annotator`  
Branch: `feature/nvt-validation-v1`

## 1. Fixed integration policy

Created:

```text
docs/NVT/NVT_INTEGRATION_POLICY_V1.md
```

Fixed decisions:

```text
current Normal Run remains BASELINE
NVT0-NVT8 production semantics unchanged
NVT9 only for production promotion
promotion is responsibility-layer based
candidate absence cannot be hidden by selector tuning
held-out validation required
NR regression required
MT4 verification required
baseline / rollback path retained through initial promotion
experimental prefix = NCA_NVT__
production prefix = NCA_DRAW__
runtime remains local / deterministic
```

## 2. Important historical-data gap found

The production Normal Run exporter uses 600 closed bars per timeframe.

For a corpus extending roughly 40 days back from 2026-09-15:

```text
D1 600 bars: sufficient
H4 600 bars: generally sufficient
H1 600 bars: about 25 calendar days of 24h bars before weekend adjustment -> insufficient for earliest corpus cases
M15 600 bars: about 6.25 calendar days of 24h bars before weekend adjustment -> insufficient for most corpus cases
```

Therefore NVT historical replay must not depend on the production 600-bar `live_input` files.

Resolution:

```text
mt4/NCA_NVT_HistoryExporter.mq4
```

was added as research-only deep-history exporter with default 6000 closed bars and isolated output:

```text
noda_draw/nvt_input/NVT_<XM_SYMBOL>_<TF>.csv
```

Production `NCA_NormalRun_Exporter`, `live_input`, snapshots, and drawings remain untouched.

## 3. NVT2 runner corrected

`setup/run_nvt2_usdjpy_corpus.ps1` now reads only NVT deep-history input.

The five teacher-video date upper bounds remain provisional; each candidate dump records `effective_last_closed_bar`, and NVT5 will later tighten event-level exact cutoffs.

## 4. NVT3 implemented

Implemented:

```text
tools/nvt/compare_teacher.py
tools/nvt/scoring.py
tests/selftest_nvt3.py
setup/run_nvt3_usdjpy_cases.ps1
setup/RUN_NVT3_USDJPY_CASES.cmd
```

NVT3 currently supports:

```text
STRUCTURE_SCALE_MATCH
NO_LINE_MATCH
CANDIDATE_PRESENT / CANDIDATE_ABSENT
ANCHOR_MATCH when Ground Truth anchors are known
SELECTION when the teacher candidate exists
CHANNEL status kept separate / pending until teacher CH anchor is reviewed
```

Unknown teacher anchor timestamps are not guessed and do not become false mismatch results; they remain `PENDING_GROUND_TRUTH`.

## 5. Symbol policy in research comparison

Production canonical symbol policy remains exact XM `Symbol()`.

NVT comparison accepts only one explicit reference-notation equivalence for the initial corpus:

```text
USDJPY <-> USDJPY#
```

No broader alias guessing is introduced.

## 6. Production boundary audit

```text
production tools/live_draw modified by NVT: NO
production Normal Run semantics modified: NO
production 600-bar exporter modified: NO
NCA_DRAW__ semantics modified: NO
trade authority added: NO
TC dependency added: NO
ChatGPT runtime dependency added: NO
NODA Engine write-back added: NO
```

## 7. Next executable sequence on host

After updating the branch on the Windows/MT4 host:

```text
1. compile/copy NCA_NVT_HistoryExporter into MT4 Scripts
2. run NCA_NVT_HistoryExporter once on USDJPY#
3. verify deep-history status/range includes the earliest corpus dates for all required TFs
4. run setup/RUN_NVT2_USDJPY_CORPUS.cmd
5. run setup/RUN_NVT3_USDJPY_CASES.cmd
6. inspect NVT3_USDJPY_METRICS.json and per-case diff reports
```

Expected initial result:

- NO-LINE cases may immediately produce meaningful mismatches;
- GT cases with exact anchors still UNKNOWN should remain `PENDING_GROUND_TRUTH` rather than false FAIL;
- NVT5 will lock exact event cutoffs/anchors before selector/lifecycle tuning.

## 8. Judgment

```text
INTEGRATION POLICY: FIXED
NVT2 CANDIDATE DUMP: IMPLEMENTED
NVT2 HISTORICAL INPUT ISOLATION: IMPLEMENTED
NVT3 DIFF ENGINE: IMPLEMENTED
NVT3 DECOMPOSED SCORING: IMPLEMENTED
NVT3 SYNTHETIC SELFTEST: ADDED
REAL CORPUS NVT2/NVT3 EXECUTION: HOST DATA REQUIRED
NVT5 EXACT TIME-FROZEN REPLAY: NOT YET IMPLEMENTED
NVT6 SELECTOR CHANGES: NOT STARTED
PRODUCTION NCA: UNCHANGED
```
