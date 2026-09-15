# NVT Turn Recognition Improvement Candidates v0.1

Status: **DRAFT / RESEARCH ONLY**  
Date: 2026-09-15  
Scope: NVT experimental validation only. Production `tools/live_draw`, Normal Run, and `NCA_DRAW__` are not changed by this document.

## Why this exists

GT_0006 suggests that the teacher can use an H1 small-Dow rebound high as a TL anchor even when the current production candidate pool does not contain the corresponding anchor pair.

The current production Turn Detector v1 has one active leg and confirms a wave extreme only after a later **closed-bar close retraces at least 38%** of that active wave. That rule is useful for confirmed larger structure, but it may suppress nested small-Dow highs/lows inside the still-active larger leg.

The goal is **not** to reduce 38% until the case passes. The goal is to determine whether a second structural layer is required.

## Candidate improvements to test

### R1. Nested Micro-Dow layer — highest priority

Keep the current 38% confirmed pivots unchanged as the large/mid structural layer.

Add a separate research-only `MICRO_DOW` layer. In a falling context, a local rebound high may become a structurally validated micro HIGH when a later local LOW breaks the preceding local LOW. Symmetrically, in a rising context, a local pullback low may become a micro LOW when a later local HIGH breaks the preceding local HIGH.

Example:

```text
LOW1 -> rebound HIGH -> LOW2
                    and LOW2 < LOW1
=> rebound HIGH is a structurally validated micro-Dow HIGH
```

This is closer to the visual logic observed in GT_0006 than merely lowering the 38% threshold.

Required safeguards:
- closed bars only;
- minimum bar separation;
- no automatic promotion to large/mid structure;
- explicit structure-scale ownership;
- regression against GT_0005 / GT_0007 NO-LINE cases.

### R2. Confirmed + provisional pivot pools

Maintain two distinct pools:
- `CONFIRMED_38`: current production pivots;
- `PROVISIONAL_MICRO`: local/nested structural pivots not yet confirmed by 38%.

Candidates generated from provisional pivots must retain source/confidence metadata. They must not silently become production-equivalent candidates.

Benefit: candidate recall improves without weakening the meaning of the existing 38% confirmation.

Risk: candidate explosion. A selector must never receive an unbounded list without scale and recency gates.

### R3. Multi-scale turn recognition

Represent at least two simultaneous structural scales instead of forcing all price action into one active leg:
- large/mid confirmed structure;
- nested small-Dow structure.

This is a stronger architectural change than R1 and should be attempted only if GT_0006 plus additional teacher cases show the same pattern repeatedly.

### R4. Cluster-edge metadata

The teacher repeatedly refers to a cluster edge, especially the right edge, when several nearby highs/lows are geometrically valid.

Do not collapse the cluster to one point immediately. Preserve metadata such as:
- cluster membership;
- left/right edge rank;
- highest/lowest member;
- time span;
- source scale.

This belongs after turn recall. It cannot recover a teacher anchor that was never recognized as a structural point.

### R5. Wick-outlier tag, not hard deletion

Teacher evidence shows both wick-to-wick use and cases where an unusually long wick may be treated as noise.

Therefore add a research tag such as `WICK_OUTLIER_CANDIDATE` rather than a global rule to always include or always remove long wicks. Later selection can compare wick anchor vs body/cluster alternatives.

### R6. Candidate identity / duplicate audit

GT_0003 showed repeated candidate rows sharing the same current `candidate_id` while structural metrics such as `turn_span` differed.

Before NVT6 scoring, audit whether candidate identity must include additional structural context or whether upstream pivot duplication should be deduplicated. Selector experiments are unreliable if one geometric candidate is represented multiple times with conflicting metadata.

### R7. Threshold sensitivity is diagnostic only

A temporary sensitivity matrix (for example several retracement thresholds around the current 38%) may be useful to understand why a pivot is suppressed.

It must **not** be used as a direct tuning method such as “lower the threshold until GT_0006 appears.” Teacher material itself uses 38.2% concepts, and the likely issue is nested scale rather than a single bad constant.

## Preferred research order

1. Run GT_0006 turn-recall diagnostic.
2. Determine whether teacher-like local highs are:
   - inside a production FALLING leg,
   - active extremes that fail 38% confirmation,
   - confirmed pivots rejected later by candidate gates.
3. If nested highs dominate, prototype R1 only in `tools/nvt/`.
4. Re-test GT_0001–GT_0007, especially NO-LINE negatives.
5. Only if R1 is insufficient, consider R2/R3.
6. Keep R4/R5 as selector-support metadata, not substitutes for turn recall.
7. Resolve R6 before NVT6 production-like scoring.

## Promotion rule

None of these ideas are production rules. Promotion remains governed by `NVT_INTEGRATION_POLICY_V1.md`: held-out evidence, NR regression, MT4 verification, and NVT9 approval are required before any production change.
