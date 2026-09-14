# NR7-1 USDJPY# Regression Audit — 2026-09-15

Status: **FINAL PASS / CLOSED**

Repository: `toootakeooot-bit/noda-chart-annotator`  
Branch: `feature/normal-run-v1`  
Target: `USDJPY#`

## 1. Purpose

Verify that the Normal Run / History Rebuild implementation preserves the known-good USDJPY structural drawing semantics while adding true immediate-previous reconstruction, validated snapshot publication, renderer ownership isolation, and fail-safe retention.

Detector / geometry / selection semantics were not changed merely to make the regression pass.

## 2. Final host evidence

All evidence below was observed on the target XM MT4 host.

### A. Export — PASS

`NCA_NormalRun_Exporter` completed on `USDJPY#` with:

```text
D1=600
H4=600
H1=600
M15=600
```

Closed-bar input for all four required timeframes passed.

### B. Automated Normal Run / regression — PASS

The final automated runner completed with:

```text
NR7-1 AUTOMATED FINAL CHECK PASS
```

Automated evidence included:

```text
snapshot.status = PASS
snapshot.rows = 64
snapshot.unique_object_ids = 64
overall_status = PASS
```

The regression uses the same exported closed-bar dataset and checks the published Normal Run state against baseline structural-event geometry.

### C. Current + true previous reconstruction — PASS

Normal Run rebuild starts from history rather than treating the prior saved run as authoritative `previous`.

For displayed structures, `previous` is generation-adjacent to `current` in the reconstructed lifecycle sequence.

Observed H1 state:

```text
LARGE_DOW previous = G019
LARGE_DOW current  = G020
MID_DOW   previous = G027
MID_DOW   current  = G028
```

### D. MT4 render — PASS

Observed renderer results:

```text
USDJPY# H1  objects=16  PASS
USDJPY# M15 objects=16  PASS
USDJPY# H4  objects=16  PASS
USDJPY# D1  objects=16  PASS
```

Expected snapshot object count:

```text
4 timeframes
x 2 structure levels (LARGE_DOW / MID_DOW)
x 2 generations (previous / current)
x 4 drawing roles (TL / CH / TL_ZONE_EDGE / CH_ZONE_EDGE)
= 64 rows
```

Observed snapshot row count = **64**.

### E. H1 object-level ownership evidence — PASS

MT4 object list for `USDJPY#,H1` showed 16 production-managed `NCA_DRAW__` objects:

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

Existing `NCA_TEST__` objects remained present, proving the renderer did not indiscriminately delete non-`NCA_DRAW__` objects in the observed run.

## 3. Optimized performance — PASS versus captured reference

Pre-optimization captured Normal Run:

```text
380.62 seconds
```

Optimized Normal Run host measurement:

```text
49.755 seconds
```

Result:

```text
improved_vs_old_reference = true
reduction ≈ 86.9%
speedup ≈ 7.65x
```

The optimization:

- replays expensive candidate generation only at confirmed structural Turn event points;
- skips ordinary closed-bar prefixes that cannot create a replacement TL under Lifecycle v1;
- removes duplicate history rebuild from regression Step B;
- retains the same Normal Run / history-rebuild responsibility boundary.

No hard production performance threshold has been fixed. Therefore this audit records **PASS versus the captured 380.62 s reference**, not a universal latency SLA.

Future performance tuning may continue separately without reopening NR7-1 unless it changes reconstruction semantics.

## 4. File-level safe publication — PASS

The automated retention probe deliberately attempted to publish an invalid empty drawing state through the production safe-publication path.

Observed:

```text
expected_publish_failure_observed = true
snapshot_hash_unchanged = true
overall_status = PASS
```

Failure type observed:

```text
ValueError: snapshot has no drawing rows
```

The previously published valid snapshot remained byte-identical after the failed publication attempt.

## 5. Actual MT4 renderer failure-retention — PASS

The valid snapshot was temporarily hidden while existing H1 `NCA_DRAW__` objects remained displayed.

The actual MT4 production renderer was then run once.

Observed Expert log:

```text
NCA NormalRun Renderer: no validated renderable rows; keeping existing drawing. code=-1
```

After that failure path, the H1 object list still contained the existing production-managed `NCA_DRAW__` objects. The renderer therefore did not delete the last valid drawing when its snapshot was unavailable.

This directly verifies the renderer-side fail-safe boundary:

```text
snapshot unavailable/invalid
-> validation fails before DeleteOwnedObjects()
-> existing NCA_DRAW__ remains
```

## 6. Snapshot restoration — PASS

After the renderer failure probe, the helper restored the valid snapshot.

Observed:

```text
NR7-1 SNAPSHOT RESTORE PASS
NR7-1 RENDERER FAILURE PROBE HELPER PASS
```

Restored snapshot SHA256:

```text
B564BD20A0110DF1A173D6F3D499C206BDF14BC88E169BC04ADFCED533CE7F08
```

The helper verified restored size/hash identity against the original snapshot.

## 7. Safety / scope maintained

NR7-1 introduced no:

- TC dependency;
- ChatGPT runtime dependency;
- NODA Engine write-back;
- trade execution;
- order / SL / TP / lot / ticket control.

The specification baseline branch remains unchanged.

## 8. Final audit judgment

```text
NR7-1 USDJPY#
STATUS: FINAL PASS / CLOSED

4TF EXPORT: PASS (600 each)
AUTOMATED FINAL CHECK: PASS
SNAPSHOT: PASS 64/64
CURRENT + TRUE PREVIOUS: PASS
H1 RENDER: PASS 16
M15 RENDER: PASS 16
H4 RENDER: PASS 16
D1 RENDER: PASS 16
NCA_DRAW__ OWNERSHIP: PASS
NON-NCA_DRAW__ RETENTION: PASS
OPTIMIZED PERFORMANCE: PASS VS REFERENCE (49.755 s vs 380.62 s)
FILE-LEVEL SAFE PUBLICATION: PASS
ACTUAL MT4 FAILURE-RETENTION: PASS
SNAPSHOT RESTORE/HASH: PASS

NR7-1 PRODUCTION REGRESSION GATE: PASS
```

## 9. Next gate

Proceed to NR7 multi-symbol runtime verification without changing the validated USDJPY detector / geometry / selection semantics:

```text
NR7-2 GOLD#
NR7-3 US100Cash#
NR7-4 JP225Cash#
NR7-5 one additional XM MT4 symbol
```

The goal of the remaining NR7 gates is symbol-generalization verification, not re-design of the USDJPY-proven drawing semantics.
