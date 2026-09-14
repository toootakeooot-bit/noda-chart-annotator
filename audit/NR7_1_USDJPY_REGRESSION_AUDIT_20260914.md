# NR7-1 USDJPY# Regression Audit — 2026-09-15

Status: **FUNCTIONAL RUNTIME PASS / OPTIMIZED PERFORMANCE + FAILURE-PRESERVATION FINALIZATION READY**

Repository: `toootakeooot-bit/noda-chart-annotator`  
Branch: `feature/normal-run-v1`  
Target: `USDJPY#`

## 1. Purpose

Verify that the new Normal Run / History Rebuild implementation preserves the known-good USDJPY structural drawing semantics while adding true immediate-previous reconstruction and safe publication.

This is a regression gate. Detector / geometry / selection semantics must not be changed merely to make the test pass.

## 2. Automated regression criterion

The optimized Normal Run reconstructs lifecycle generations only at confirmed structural Turn events, not on every ordinary closed bar.

`tools/nr7_1_usdjpy_regression.py` now reuses the already published Normal Run state and audit rather than rebuilding the same 600-bar histories a second time.

For each of `D1 / H4 / H1 / M15`:

1. identify the last confirmed structural event from the same Normal Run closed-bar input;
2. run the existing detector / candidate-builder / Large-Mid selector once at that structural-event boundary to obtain the baseline selected geometry;
3. load the published Normal Run reconstructed state / audit from Step A;
4. compare the published Normal Run final `current` geometry to the baseline event-boundary geometry;
5. verify that, when a `previous` generation exists, it is generation-adjacent to `current` and corresponds to the second-last reconstructed lifecycle transition for that structure level.

Comparison is based on geometry, not symbol aliases or generated line IDs:

- direction;
- anchor1 time / price;
- anchor2 time / price;
- CH offset;
- zone width.

This removes the former duplicate rebuild cost from regression Step B.

## 3. Actual host evidence — FUNCTIONAL PASS

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

### Automated regression — pre-optimization captured run

`RUN_NR7_1_USDJPY.cmd` completed with:

```text
snapshot.status = PASS
snapshot.rows = 64
snapshot.unique_object_ids = 64
overall_status = PASS
NR7-1 AUTOMATED CHECK PASS
```

This established the geometry / reconstructed-previous / snapshot gate for the captured USDJPY# dataset before performance optimization.

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

## 5. Functional PASS judgment

The following NR7-1 functional checks are PASS:

```text
MT4 EXPORTER COMPILE/RUN: PASS
USDJPY# 600 CLOSED BARS x 4TF: PASS
AUTOMATED BASELINE-vs-REBUILD REGRESSION: PASS ON CAPTURED RUN
TRUE IMMEDIATE PREVIOUS REBUILD CHECK: PASS ON CAPTURED RUN
SNAPSHOT VALIDATION: PASS (64/64)
H1 RENDER: PASS (16)
M15 RENDER: PASS (16)
H4 RENDER: PASS (16)
D1 RENDER: PASS (16)
NCA_DRAW__ OWNERSHIP: PASS ON OBSERVED TEST
NON-NCA_DRAW__ RETENTION: PASS ON OBSERVED NCA_TEST__ OBJECTS
```

Therefore **NR7-1 USDJPY# functional runtime regression is PASS**.

## 6. Performance optimization implemented

The original chronological replay evaluated nearly every historical prefix and took approximately:

```text
380.62 seconds
```

The optimized implementation now:

- obtains confirmed Turn event indices from closed-bar history;
- performs expensive channel-candidate generation / selection only at those structural confirmation points;
- skips ordinary closed-bar prefixes that cannot create a replacement TL under Lifecycle v1;
- prints progress per timeframe;
- reuses the published rebuild state/audit in regression Step B instead of rebuilding again.

`setup/run_nr7_1_usdjpy.ps1` now records:

```text
NR7_1_USDJPY#_performance.json
```

including:

- old reference = 380.62 sec;
- optimized elapsed time;
- whether the optimized run improved on the old reference.

No hard production performance threshold has been fixed yet. Host timing of the optimized revision is still required.

Performance status: **IMPLEMENTED / HOST RE-TEST PENDING**.

## 7. Safe-publication failure retention probe implemented

Added:

```text
tools/nr7_1_safe_retention.py
```

The automated probe deliberately attempts to publish an invalid empty drawing state through the production safe-publication function. PASS requires:

```text
validation failure occurs before publication
+
existing published snapshot SHA256 remains byte-identical
```

This is now included as Step C of `setup/run_nr7_1_usdjpy.ps1`.

File-level safe publication status: **IMPLEMENTED / HOST RUN PENDING**.

## 8. Actual MT4 renderer failure-retention probe prepared

Added:

```text
setup/RUN_NR7_1_RENDERER_FAILURE_PROBE.cmd
setup/run_nr7_1_renderer_failure_probe.ps1
```

The helper:

1. hashes the valid USDJPY# snapshot;
2. temporarily moves it out of the renderer path;
3. instructs the user to run the actual `NCA_NormalRun_Renderer` once on USDJPY# H1;
4. expected production renderer behavior is:

```text
no validated renderable rows; keeping existing drawing. code=-1
```

5. existing 16 `NCA_DRAW__` H1 objects must remain;
6. the helper automatically restores the valid snapshot;
7. restored snapshot SHA256 / byte size must match the original.

This exercises the actual renderer's fail-safe boundary without intentionally deleting or changing the displayed managed objects.

Actual MT4 failure-retention status: **HELPER READY / HOST EVIDENCE PENDING**.

## 9. Safety / scope

NR7-1 does not add or permit:

- TC dependency;
- ChatGPT runtime dependency;
- NODA Engine write-back;
- trade execution;
- order / SL / TP / lot / ticket control.

The specification baseline branch remains unchanged.

## 10. Current audit judgment

```text
NR7-1 USDJPY#
FUNCTIONAL RUNTIME REGRESSION: PASS
4TF EXPORT: PASS
SNAPSHOT: PASS 64/64
4TF RENDER: PASS 16 EACH
CURRENT + TRUE PREVIOUS: PASS ON CAPTURED RUN
OWNED PREFIX BEHAVIOR: PASS ON OBSERVED RUN
OPTIMIZED REPLAY: IMPLEMENTED
DUPLICATE REGRESSION REBUILD: REMOVED
OPTIMIZED PERFORMANCE: HOST RE-TEST PENDING
FILE-LEVEL SAFE PUBLICATION: HOST RUN PENDING
ACTUAL MT4 FAILURE-RETENTION: HOST PROBE PENDING
FULL PRODUCTION GATE: NOT YET CLAIMED
```
