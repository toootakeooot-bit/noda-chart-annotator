# NR7-2 GOLD# Symbol-Generalization Audit — 2026-09-15

Status: **MT4 EXPORT PASS / AUTOMATED RUN PENDING**

Repository: `toootakeooot-bit/noda-chart-annotator`  
Branch: `feature/normal-run-v1`  
Target XM symbol: `GOLD#`

## 1. Purpose

NR7-2 verifies symbol generalization after NR7-1 USDJPY# closed successfully.

The goal is not to redesign detector / geometry / lifecycle semantics. The goal is to prove that the same Normal Run path works for a materially different XM symbol without symbol-specific allowlists, alias maps, or USDJPY hard-coding.

## 2. Reused production path

NR7-2 uses the same production-path components already validated on USDJPY#:

```text
NCA_NormalRun_Exporter
 -> tools/run_normal.py
 -> Normal Run history rebuild
 -> validated NORMAL_GOLD#_live_snapshot.csv
 -> NCA_NormalRun_Renderer
```

No GOLD-specific detector or drawing logic is permitted.

Exact MT4 `Symbol()` value `GOLD#` remains the canonical symbol identity in state / audit / snapshot.

## 3. Generic harness

Added and ready:

```text
tools/nr7_symbol_regression.py
tools/nr7_safe_retention.py
setup/run_nr7_symbol.ps1
setup/RUN_NR7_2_GOLD.cmd
```

These are symbol-parameterized. USDJPY#-specific NR7-1 evidence remains unchanged.

## 4. Actual MT4 export evidence — PASS

Observed on the target XM MT4 host on 2026-09-15.

`NCA_NormalRun_Exporter` completed on `GOLD#` and reported:

```text
NCA NORMAL RUN EXPORT COMPLETE: GOLD# D1=600 H4=600 H1=600 M15=600
```

The same completion line was observed from multiple GOLD# chart timeframes because the exporter was run more than once. This is not required for normal operation, but it confirms that the one-shot exporter resolves the exact chart symbol consistently regardless of which GOLD# timeframe initiated it.

Result:

```text
GOLD# exact symbol identity: PASS
D1 closed bars: 600 PASS
H4 closed bars: 600 PASS
H1 closed bars: 600 PASS
M15 closed bars: 600 PASS
```

## 5. Automated checks to run next

`setup/RUN_NR7_2_GOLD.cmd` will perform:

1. shared Normal Run synthetic selftest;
2. Normal Run rebuild for D1 / H4 / H1 / M15;
3. timing capture;
4. structural-event baseline versus published Normal Run current geometry;
5. true immediate-previous generation adjacency check;
6. snapshot schema / exact symbol / timeframe / role / generation-role / unique-ID validation;
7. failed-publication safe-retention probe proving the valid GOLD# snapshot is not overwritten by an invalid new state.

Expected automated PASS contract:

```text
all_inputs_present = true
normal_run_state_present = true
normal_run_audit_pass = true
same_final_current_geometry_as_baseline = true
previous_is_immediate_rebuilt_generation = true
snapshot_valid = true
safe snapshot retention = PASS
overall_status = PASS
```

Snapshot object counts are derived from the actual validated GOLD# snapshot; NR7-2 does not assume every symbol/timeframe must always have exactly 16 rows.

## 6. Host checks remaining after automated PASS

1. run `setup/RUN_NR7_2_GOLD.cmd` and require automated PASS;
2. run `NCA_NormalRun_Renderer` once on GOLD# D1 / H4 / H1 / M15;
3. renderer object counts must match the snapshot-derived expected count printed by the runner;
4. `Ctrl+B` on at least H1 must show production names beginning `NCA_DRAW__NCA_GOLD#_...` and preserve non-`NCA_DRAW__` objects.

A repeat of the NR7-1 renderer-failure-retention probe is optional unless GOLD# exposes symbol-specific failure behavior; the production renderer code path is shared and already closed on USDJPY#.

## 7. Performance treatment

NR7-1 optimized USDJPY# measured 49.755 seconds on the user's host. That is evidence for USDJPY#, not a fixed cross-symbol threshold.

NR7-2 records GOLD# elapsed time independently. No detector/selection change may be made solely to force GOLD# under the USDJPY# timing.

## 8. Scope / safety unchanged

NR7-2 introduces no:

- TC dependency;
- ChatGPT runtime dependency;
- NODA Engine write-back;
- trade/order authority;
- symbol allowlist.

## 9. Current judgment

```text
NR7-2 GOLD#
GENERIC REGRESSION HARNESS: READY
GENERIC SAFE RETENTION: READY
DOUBLE-CLICK GOLD RUNNER: READY
DETECTOR / SELECTION SEMANTICS CHANGED: NO
GOLD# MT4 EXPORT: PASS (600 x 4TF)
GOLD# AUTOMATED RUN: PENDING USER PC
GOLD# 4TF RENDER: PENDING USER PC
FINAL NR7-2 PASS: NOT YET CLAIMED
```
