# NR7-1 USDJPY# Regression Audit — 2026-09-14

Status: **AUTOMATED HARNESS READY / MT4 RUNTIME EVIDENCE PENDING**

Repository: `toootakeooot-bit/noda-chart-annotator`  
Branch: `feature/normal-run-v1`  
Target: `USDJPY#`

## 1. Purpose

Verify that the new Normal Run / History Rebuild implementation preserves the known-good final USDJPY drawing-selection semantics while adding true immediate-previous reconstruction and safe publication.

This is a regression gate. It must not change detector/geometry/selection semantics merely to make the test pass.

## 2. Automated regression criterion

`tools/nr7_1_usdjpy_regression.py` uses the exact same Normal Run closed-bar input files for both comparison paths.

For each of `D1 / H4 / H1 / M15`:

1. run the existing detector / candidate-builder / Large-Mid selector once on the full closed-bar history to obtain the legacy/baseline final selected geometry;
2. run Normal Run chronological history rebuild from an empty lifecycle state;
3. compare the Normal Run final `current` geometry to the baseline final selected geometry;
4. verify that, when a `previous` generation exists, it is generation-adjacent to `current` and corresponds to the second-last lifecycle transition reconstructed for that structure level.

Comparison is based on geometry, not symbol aliases or generated line IDs:

- direction;
- anchor1 time / price;
- anchor2 time / price;
- CH offset;
- zone width.

Expected result:

```text
legacy full-history final selection geometry
==
Normal Run rebuilt current geometry
```

for both `LARGE_DOW` and `MID_DOW` wherever a selection exists.

## 3. Normal Run publication checks

The regression also requires:

- all four Normal Run input CSV files present;
- `NORMAL_USDJPY#_run_audit.json` status = `PASS`;
- `snapshot_published = true`;
- validated snapshot exists and is non-empty;
- snapshot symbol = exact XM symbol `USDJPY#`;
- timeframe in D1/H4/H1/M15;
- role in TL/CH/TL_ZONE_EDGE/CH_ZONE_EDGE;
- generation role in CURRENT/PREVIOUS;
- object IDs unique;
- price fields numeric.

## 4. One-command host runner

Added:

`setup/run_nr7_1_usdjpy.ps1`

Host-side sequence:

```text
MT4: run NCA_NormalRun_Exporter once on USDJPY#
 -> setup/run_nr7_1_usdjpy.ps1
      -> tools/run_normal.py
      -> tools/nr7_1_usdjpy_regression.py
 -> PASS/FAIL JSON report
```

Output report:

```text
%APPDATA%\MetaQuotes\Terminal\Common\Files\noda_draw\live_output\NR7_1_USDJPY#_regression.json
```

The runner also records elapsed Normal Run time to the console for performance observation.

## 5. Automated PASS conditions

NR7-1 automated gate is PASS only when all are true:

```text
same_final_current_geometry_as_baseline = true
previous_is_immediate_rebuilt_generation = true
all_inputs_present = true
normal_run_audit_pass = true
snapshot_valid = true
```

Any failure returns a non-zero process exit code.

## 6. MT4 runtime checks still required

These cannot be truthfully certified from GitHub-only execution and require the user's actual MT4① host:

1. `NCA_NormalRun_Exporter.mq4` compiles in the target XM MT4 environment.
2. Exporter writes valid D1/H4/H1/M15 closed-bar CSV files for `USDJPY#`.
3. `NCA_NormalRun_Renderer.mq4` compiles in the target environment.
4. Renderer displays the validated snapshot on each supported timeframe.
5. Current + previous TL/CH placement is visually reasonable versus the known-good USDJPY chart.
6. Manual/user objects remain untouched.
7. A failed rebuild / invalid new snapshot does not erase the last valid displayed NCA drawing.
8. Normal Run elapsed time with 600 bars x 4 TF is operationally acceptable.

## 7. Safety / scope

NR7-1 does not add or permit:

- TC dependency;
- ChatGPT runtime dependency;
- NODA Engine write-back;
- trade execution;
- order/SL/TP/lot/ticket control.

The baseline specification branch remains unchanged.

## 8. Current audit judgment

```text
NR7-1 USDJPY#
AUTOMATED HARNESS: READY
CODE-LEVEL REGRESSION CRITERIA: FIXED
HOST RUNNER: READY
ACTUAL USDJPY# DATA EXECUTION: PENDING USER PC
MT4 COMPILE: PENDING USER PC
MT4 VISUAL REGRESSION: PENDING USER PC
FINAL NR7-1 PASS: NOT YET CLAIMED
```
