# NR7-1 USDJPY# Regression Audit — 2026-09-15

Status: **FUNCTIONAL RUNTIME PASS / PERFORMANCE + FAILURE-INJECTION PENDING**

Repository: `toootakeooot-bit/noda-chart-annotator`  
Branch: `feature/normal-run-v1`  
Target: `USDJPY#`

## 1. Purpose

Verify that the new Normal Run / History Rebuild implementation preserves the known-good final USDJPY drawing-selection semantics while adding true immediate-previous reconstruction and safe publication.

This is a regression gate. Detector / geometry / selection semantics must not be changed merely to make the test pass.

## 2. Automated regression criterion

`tools/nr7_1_usdjpy_regression.py` uses the same Normal Run closed-bar input files for both comparison paths.

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

## 3. Actual host evidence — PASS

Observed on the target XM MT4 host.

### Export

`NCA_NormalRun_Exporter` completed on `USDJPY#` with:

```text
D1=600
H4=600
H1=600
M15=600
```

Closed-bar export for all four required timeframes therefore passed.

### Automated regression

`RUN_NR7_1_USDJPY.cmd` completed with:

```text
snapshot.status = PASS
snapshot.rows = 64
snapshot.unique_object_ids = 64
overall_status = PASS
NR7-1 AUTOMATED CHECK PASS
```

This establishes the automated geometry / reconstructed-previous / snapshot gate for the captured USDJPY# dataset.

### MT4 render

Observed renderer results:

```text
USDJPY# H1  objects=16  PASS
USDJPY# M15 objects=16  PASS
USDJPY# H4  objects=16  PASS
USDJPY# D1  objects=16  PASS
```

Total expected Normal Run snapshot rows:

```text
4 timeframes
x 2 structure levels (LARGE_DOW / MID_DOW)
x 2 generations (previous / current)
x 4 drawing roles (TL / CH / TL_ZONE_EDGE / CH_ZONE_EDGE)
= 64 rows
```

Observed snapshot row count = **64**, consistent with the render contract.

## 4. H1 object-level evidence

MT4 object list for `USDJPY#,H1` showed exactly 16 production-managed Normal Run objects:

```text
LARGE_DOW G019 = 4 objects
LARGE_DOW G020 = 4 objects
MID_DOW   G027 = 4 objects
MID_DOW   G028 = 4 objects
```

Each generation contained:

```text
TL
CH
TL_ZONE_EDGE
CH_ZONE_EDGE
```

Interpretation for the reconstructed H1 state:

```text
LARGE_DOW previous = G019
LARGE_DOW current  = G020
MID_DOW   previous = G027
MID_DOW   current  = G028
```

The same H1 object list still contained the prior `NCA_TEST__` objects. This is direct evidence that the production renderer did not indiscriminately delete non-`NCA_DRAW__` objects during this test.

## 5. Publication checks — PASS

The automated regression established:

- all four Normal Run input CSV files present;
- Normal Run audit status = `PASS`;
- `snapshot_published = true`;
- validated snapshot non-empty;
- exact snapshot symbol = `USDJPY#`;
- supported timeframe values only;
- supported drawing roles only;
- CURRENT / PREVIOUS generation roles only;
- unique object IDs;
- numeric prices;
- 64 valid snapshot rows.

## 6. Functional PASS judgment

The following NR7-1 functional checks are now PASS:

```text
MT4 EXPORTER COMPILE/RUN: PASS
USDJPY# 600 CLOSED BARS x 4TF: PASS
AUTOMATED BASELINE-vs-REBUILD REGRESSION: PASS
TRUE IMMEDIATE PREVIOUS REBUILD CHECK: PASS
SNAPSHOT VALIDATION: PASS (64/64)
H1 RENDER: PASS (16)
M15 RENDER: PASS (16)
H4 RENDER: PASS (16)
D1 RENDER: PASS (16)
NCA_DRAW__ OWNERSHIP: PASS ON OBSERVED TEST
NON-NCA_DRAW__ RETENTION: PASS ON OBSERVED NCA_TEST__ OBJECTS
```

Therefore **NR7-1 USDJPY# functional runtime regression is PASS**.

## 7. Items not yet closed

Two items remain outside the functional PASS and must not be silently treated as complete:

### A. Performance

The captured pre-optimization Normal Run took approximately:

```text
380.62 seconds
```

This is functionally correct but not an acceptable target for routine Normal Run operation. A performance optimization has been implemented separately to reduce rebuild evaluations to structural/confirmed-turn event points, but that optimized revision still requires host timing verification.

Performance status: **PENDING RE-TEST**.

### B. Failure-injection / last-valid-drawing preservation

The safe-publication design is implemented, but the host test has not yet deliberately supplied a failed rebuild / invalid snapshot to prove that the previously displayed valid `NCA_DRAW__` drawing remains intact.

Failure-preservation status: **PENDING HOST TEST**.

## 8. Safety / scope

NR7-1 does not add or permit:

- TC dependency;
- ChatGPT runtime dependency;
- NODA Engine write-back;
- trade execution;
- order / SL / TP / lot / ticket control.

The specification baseline branch remains unchanged.

## 9. Current audit judgment

```text
NR7-1 USDJPY#
FUNCTIONAL RUNTIME REGRESSION: PASS
4TF EXPORT: PASS
AUTOMATED REGRESSION: PASS
SNAPSHOT: PASS 64/64
4TF RENDER: PASS 16 EACH
CURRENT + TRUE PREVIOUS: PASS
OWNED PREFIX BEHAVIOR: PASS ON OBSERVED RUN
PERFORMANCE: PENDING RE-TEST
FAILURE-INJECTION SAFE-KEEP: PENDING
FULL PRODUCTION GATE: NOT YET CLAIMED
```
