# NVT1 Video Event Review Audit — 2026-09-15

Status: **PASS FOR DRAFT CASE REGISTRATION / NOT YET LOCKED**

Repository: `toootakeooot-bit/noda-chart-annotator`  
Branch: `feature/nvt-validation-v1`

## 1. Sources reviewed

USDJPY primary corpus:

```text
2026-08-08  分析共有 26-8-8.mkv
2026-08-22  分析共有 26-8-22.mkv
2026-08-30  分析共有_26-8-30.mkv
2026-09-05  分析共有_26-9-5.mkv
2026-09-12  分析共有_26-9-12.mp4
```

All contain timed Japanese subtitles; event windows were aligned to chart frames.

## 2. NVT1 outputs created

```text
nvt/cases/NVT1_DRAFT_CASE_REGISTRY_20260915.md
nvt/ground_truth/GT_0001.json
nvt/ground_truth/GT_0002.json
nvt/ground_truth/GT_0003.json
nvt/ground_truth/GT_0004.json
nvt/ground_truth/GT_0005.json
nvt/ground_truth/GT_0006.json
nvt/ground_truth/GT_0007.json
nvt/reports/NVT_RULE_EVIDENCE_MATRIX_V0_1.md
docs/NVT/NVT_SCHEMA_AMENDMENT_01_DRAFT.md
```

## 3. Visually confirmed core cases

- `GT_0001`: D1 cluster-edge anchor selection for secondary uptrend TL.
- `GT_0002`: D1 channel update plus retained original/reference channel.
- `GT_0003`: H4 contextual wick/noise review.
- `GT_0004`: D1 persistent original reference preferred over newer PC re-anchor.
- `GT_0005`: H1 structural-scale mismatch -> expected no line.
- `GT_0006`: H1 multiple candidate highs + gentler-angle preference.
- `GT_0007`: H1 explicit no-line; M15 internal line belongs to lower timeframe.

Exact bar timestamps/prices are intentionally not guessed.

## 4. Cross-video findings strong enough to justify NVT2

Repeated evidence supports exposing candidate facts for:

```text
structure/timeframe ownership
anchor pivot identity
high/low update validity
candidate slope/angle
TL/CH contacts
break state
anchor wick/body morphology
retained-reference continuity
```

No selector weights or production rules are fixed from these findings.

## 5. NVT2 start

NVT2 design created:

```text
docs/NVT/NVT2_CANDIDATE_DUMP_DESIGN_V1.md
```

Read-only implementation created:

```text
tools/nvt/dump_candidates.py
```

The tool reuses current production:

```text
load_ohlc_csv -> detect_turns -> build_channel_candidates -> select_large_mid
```

and emits research JSON only.

## 6. Production boundary audit

```text
tools/live_draw modified by NVT: NO
Normal Run semantics modified by NVT: NO
NCA_DRAW__ modified by NVT: NO
trade authority added: NO
ChatGPT runtime dependency added: NO
```

## 7. Remaining NVT1/NVT2 evidence gap

Hard regression cannot yet be claimed because exact teacher-decision market cutoffs and bar-level anchors have not been reproduced from historical OHLC.

Next required bridge:

```text
teacher video event
 -> exact/verified historical cutoff
 -> matching USDJPY OHLC history
 -> NVT2 candidate dump at cutoff
 -> determine CANDIDATE_PRESENT vs CANDIDATE_ABSENT
```

That bridge leads directly into NVT3 Teacher-NCA Diff and NVT5 time-frozen replay.

## 8. Judgment

```text
NVT1 SOURCE INGEST: PASS
NVT1 VIDEO/SPEECH ALIGNMENT: PASS
NVT1 DRAFT CASE REGISTRATION: PASS
NVT1 EXACT BAR ANNOTATION: PENDING
LOCKED GROUND TRUTH: NO
NVT2 DESIGN: PASS
NVT2 CANDIDATE DUMP IMPLEMENTED: YES
NVT2 REAL HISTORICAL CASE EXECUTION: PENDING OHLC/CUTOFF
PRODUCTION NCA CHANGED: NO
```
