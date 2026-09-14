# NCA Normal Run Implementation Progress — 2026-09-15

Status: **NR0-NR6 IMPLEMENTED / NR7-1 CLOSED / NR7-2 READY FOR GOLD# HOST RUN**

Repository: `toootakeooot-bit/noda-chart-annotator`  
Specification baseline branch: `feature/live-draw-baseline-v1`  
Implementation branch: `feature/normal-run-v1`

## NR0 — baseline isolation

PASS.

- implementation branch created from `feature/live-draw-baseline-v1`;
- baseline branch was not modified by implementation work;
- baseline/merge-base commit: `b332b4612c52597292bd86afd8636a11a4beddc7`.

## NR1 — user-initiated Normal Run input

IMPLEMENTED / HOST VERIFIED ON USDJPY#.

`mt4/NCA_NormalRun_Exporter.mq4`:

- one-shot MT4 Script;
- no timer / continuous monitoring;
- exact current MT4 `Symbol()` identity;
- exports closed bars only (`shift >= 1`);
- D1 / H4 / H1 / M15;
- default 600 bars per timeframe;
- writes to MT4 Common Files `noda_draw/live_input`.

## NR2 — XM symbol generalization

IMPLEMENTED / MULTI-SYMBOL RUNTIME VERIFICATION IN PROGRESS.

- exact MT4 `Symbol()` value is canonical identity;
- no USDJPY/GOLD/US100/JP225 allowlist in production Normal Run path;
- filesystem-safe fragment is used only for file paths;
- exact XM symbol remains unchanged inside state / audit / snapshot.

USDJPY# passed. GOLD# is next.

## NR3 — History Rebuild

IMPLEMENTED / OPTIMIZED / USDJPY# HOST VERIFIED.

Normal Run rebuild starts from empty lifecycle state on every run and reconstructs generations from closed-bar history.

After the initial full-prefix replay measured approximately 380.62 sec on USDJPY#, the implementation was optimized to evaluate expensive channel-candidate generation / selection only at confirmed structural Turn events.

USDJPY# optimized host measurement:

```text
49.755 seconds
```

This is approximately 86.9% shorter / 7.65x faster than the original captured run. No cross-symbol hard timing threshold has been fixed.

## NR4 — Safe Snapshot

IMPLEMENTED / USDJPY# HOST VERIFIED.

Publication order:

```text
rebuild
 -> validate state
 -> write temporary snapshot
 -> validate snapshot
 -> atomic replace only after PASS
```

Invalid publication probe proved that a valid published snapshot remains byte-identical when the candidate snapshot fails validation.

## NR5 — production renderer boundary

IMPLEMENTED / USDJPY# HOST VERIFIED.

`mt4/NCA_NormalRun_Renderer.mq4`:

- production ownership prefix = `NCA_DRAW__`;
- exact current symbol + current D1/H4/H1/M15 timeframe filter;
- two-pass read/validation before deleting owned objects;
- only `NCA_DRAW__` objects are replaceable;
- non-`NCA_DRAW__` objects remain untouched;
- no timer / polling / trade functions.

USDJPY# failure injection confirmed that when the snapshot is unavailable the renderer logs:

```text
no validated renderable rows; keeping existing drawing. code=-1
```

and keeps the existing 16 H1 `NCA_DRAW__` objects.

## NR6 — Normal Run launcher

IMPLEMENTED.

Current reusable components:

- `tools/run_normal.py`
- `setup/run_normal.ps1`
- `setup/install_normal_run_v1.ps1`
- `mt4/NCA_NormalRun_Exporter.mq4`
- `mt4/NCA_NormalRun_Renderer.mq4`

Practical production sequence remains user-initiated:

```text
MT4 Exporter once
 -> Python Normal Run once
 -> Renderer once on each desired D1/H4/H1/M15 chart
```

No continuous monitoring is introduced.

## NR7 — regression / multi-symbol runtime verification

IN PROGRESS.

### NR7-1 USDJPY# — FINAL PASS / CLOSED

Host evidence established:

```text
D1/H4/H1/M15 export: 600 each
snapshot: 64/64 PASS
D1 render: 16
H4 render: 16
H1 render: 16
M15 render: 16
current + true previous: PASS
NCA_DRAW__ ownership: PASS
non-NCA_DRAW__ retention: PASS
invalid snapshot publication retention: PASS
actual MT4 missing-snapshot drawing retention: PASS
snapshot restore SHA256: PASS
optimized elapsed: 49.755 sec
```

Detailed evidence: `audit/NR7_1_USDJPY_REGRESSION_AUDIT_20260914.md`.

### NR7 common harness — READY

Added reusable symbol-parameterized harnesses:

```text
tools/nr7_symbol_regression.py
tools/nr7_safe_retention.py
setup/run_nr7_symbol.ps1
```

The generic regression:

- compares published Normal Run current geometry to the existing selector at the last confirmed structural event;
- checks reconstructed previous-generation adjacency;
- validates exact XM symbol identity;
- validates snapshot roles / timeframes / generation roles / unique IDs;
- reports actual snapshot row counts per timeframe rather than assuming a fixed count for every symbol.

### NR7-2 GOLD# — HARNESS READY / HOST PENDING

Added:

```text
setup/RUN_NR7_2_GOLD.cmd
audit/NR7_2_GOLD_REGRESSION_AUDIT_20260915.md
```

Next host sequence:

```text
GOLD# MT4 Exporter once
 -> RUN_NR7_2_GOLD.cmd
 -> Renderer on GOLD# D1/H4/H1/M15
 -> object-count / prefix verification
```

### NR7-3 US100Cash# — RUNNER PREPARED

Added:

```text
setup/RUN_NR7_3_US100Cash.cmd
```

Execution is deferred until GOLD# passes.

### NR7-4 JP225Cash# — RUNNER PREPARED

Added:

```text
setup/RUN_NR7_4_JP225Cash.cmd
```

Execution is deferred until prior symbols pass.

### NR7-5 arbitrary XM symbol

No dedicated code is needed. `setup/run_nr7_symbol.ps1 -Symbol <exact MT4 Symbol()>` is the generic proof path for at least one additional XM symbol.

## NR8 — HL / direction arrow

NOT STARTED.

Deliberately deferred until TL/CH multi-symbol Normal Run regression is complete. Boundary scope remains unchanged; this is an implementation gap only.

## Safety boundaries preserved

No Normal Run implementation introduces:

- TC dependency;
- ChatGPT runtime dependency;
- NODA Engine write-back;
- order send / close / modify;
- SL / TP / lot / ticket authority.

Existing detector / geometry / selection semantics remain reused rather than rewritten for symbol-generalization tests.
