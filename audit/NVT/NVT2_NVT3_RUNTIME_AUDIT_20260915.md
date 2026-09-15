# NVT2 / NVT3 Runtime Audit — 2026-09-15

Status: **FIXES APPLIED / PC RE-RUN REQUIRED**

## Evidence observed on PC

NVT deep-history export completed on USDJPY# with actual terminal-loaded counts approximately:

```text
D1   2048
H4   2053
H1   2072
M15  2149
```

`BarsToExport=6000` was only a request; MT4 exported the history actually loaded/available to `iBars`.

NVT2 then progressed through older D1/H4/H1 dumps but stopped on an older M15 cutoff with:

```text
ValueError: at least 3 closed bars are required after cutoff
```

NVT3 selftest passed and GT_0001/GT_0002 began comparison, then Windows PowerShell 5.1 failed to parse `GT_0005.json` at `ConvertFrom-Json`. The Ground Truth JSON itself is valid; the failure was caused by BOM-less UTF-8 Japanese content being read through the legacy PowerShell default text encoding path.

## Root cause 1 — NVT2 over-gating

The original corpus runner required all four TFs for every video date:

```text
5 video dates x D1/H4/H1/M15
```

This was stricter than the registered Ground Truth cases require. Current GT cases depend on these unique pairs:

```text
2026-08-08 D1   -> GT_0001, GT_0002
2026-08-08 H1   -> GT_0007
2026-08-30 H4   -> GT_0003
2026-09-05 D1   -> GT_0004
2026-09-12 H1   -> GT_0005, GT_0006
```

Therefore the 2026-08-08 M15 history gap is not currently a valid reason to block NVT2.

### Fix

`setup/run_nvt2_usdjpy_corpus.ps1` now builds its execution matrix dynamically from registered Ground Truth plus the cutoff manifest and processes only Ground-Truth-required source/timeframe pairs.

Optional/unregistered TF history does not gate unrelated cases. If a future Ground Truth case requires M15 at an older date, M15 history depth becomes a real gate at that time.

## Root cause 2 — Windows PowerShell 5.1 UTF-8 handling

`GT_0005.json` contains Japanese source filename text and is stored as UTF-8. Legacy `Get-Content` behavior in Windows PowerShell 5.1 can interpret BOM-less UTF-8 through the system ANSI code page, corrupting text before `ConvertFrom-Json`.

### Fix

`setup/run_nvt3_usdjpy_cases.ps1` now reads Ground Truth and generated report JSON explicitly with:

```text
System.IO.File.ReadAllText(..., System.Text.Encoding.UTF8)
```

It also clears only stale NVT research `diff_*.json` before scoring so a previous partial run cannot contaminate current metrics.

## Production impact

None.

The fixes do not modify:

- `tools/live_draw/` semantics;
- Normal Run input/state/snapshot;
- `NCA_DRAW__` objects;
- MT4 renderer behavior;
- trade behavior.

## Re-run gate

After pulling the updated NVT branch:

```text
RUN_NVT2_USDJPY_CORPUS.cmd
 -> expected: NVT2 USDJPY GROUND-TRUTH CANDIDATE DUMP PASS

RUN_NVT3_USDJPY_CASES.cmd
 -> expected: NVT3 DIFF GENERATION COMPLETE
```

`PENDING_GROUND_TRUTH` and teacher/NCA `FAIL` classifications are valid research outcomes. Runner/tool exceptions are not.
