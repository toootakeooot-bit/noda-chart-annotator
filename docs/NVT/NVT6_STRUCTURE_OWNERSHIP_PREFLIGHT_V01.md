# NVT6 Structure Ownership Preflight v0.1

Status: **DRAFT / RESEARCH ONLY**  
Date: 2026-09-15  
Scope: NVT-only. Production `tools/live_draw/`, Normal Run, `NCA_DRAW__`, trade state, and MT4 production objects remain unchanged.

## Purpose

GT_0006 demonstrated that the current production 38% Turn Detector can preserve the large H1 structural origin while suppressing nested small-Dow rebound highs that the teacher later uses as TL alternatives. A research-only Micro-Dow layer restored those missing alternatives without weakening the 38% detector.

However, recognizing a small-Dow structure does not automatically mean H1 should draw that structure. Teacher evidence contains both positive and NO-LINE decisions, and NO-LINE itself has more than one scope.

Therefore NVT6 must not begin with selector ranking alone. A structure-ownership preflight is required first.

This does **not** change the fixed NVT0→NVT9 roadmap. It is a precondition inside NVT6, required by the fixed integration policy diagnostic order:

```text
STRUCTURE_SCALE_MATCH
 -> CANDIDATE_PRESENT
 -> ANCHOR_MATCH
 -> SELECTOR_MATCH
 -> NO_LINE_MATCH
```

## Evidence basis

### GT_0006 — positive H1 line case

Teacher evidence:
- H1 descending TL is expected;
- several structurally valid high candidates are discussed;
- gentler angle is preferred among valid alternatives;
- a very long wick may be treated as noise.

NVT findings:
- production candidate recall was absent for the teacher-like later high;
- Micro-Dow restored 12 anchor2 alternatives when the production-confirmed H1 origin `2026-09-02 04:00 / 160.387` was preserved.

### GT_0007 — timeframe-global H1 NO-LINE candidate

Teacher evidence explicitly says the H1 chart does not need a line; if a line is desired, use the M15/internal-wave structure. This is the strongest current negative control for H1 ownership.

### GT_0005 — structure-specific NO-LINE candidate

GT_0005 is different. The teacher rejects the **apparent structure being discussed** because it belongs to another structural scale. Shortly afterward GT_0006 discusses a different valid H1 descending TL on the same source/cutoff.

Therefore GT_0005 must **not** be interpreted as `no H1 line of any kind may exist`. It is a candidate/structure-specific ownership control. The rejected structure must be identified before it can be used as a clean candidate-level negative label.

This distinction is recorded in `NVT_SCHEMA_AMENDMENT_01_DRAFT.md` as a required `no_line_scope` concept.

## Research candidate provenance

Every research TL candidate shall retain its source scale for both anchors:

```text
P38_P38     = CONFIRMED_38 -> CONFIRMED_38
P38_MICRO   = CONFIRMED_38 -> MICRO_DOW
MICRO_P38   = MICRO_DOW -> CONFIRMED_38
MICRO_MICRO = MICRO_DOW -> MICRO_DOW
```

The provenance is evidence, not the final ownership rule.

Initial working hypothesis:

```text
P38_P38     : native same-timeframe structure candidate
P38_MICRO   : same-timeframe bridge candidate; may be H1-owned
MICRO_MICRO : likely nested/internal structure; do not assume H1 ownership
MICRO_P38   : unusual transition; keep UNRESOLVED until evidence supports it
```

This hypothesis must be tested against positive cases and correctly scoped NO-LINE evidence. It must not be hard-coded as production behavior.

## Ownership outputs

The eventual experimental gate may return:

```text
OWNED_CANDIDATE
INTERNAL_ONLY
UNRESOLVED
```

`OWNED_CANDIDATE` means only that the candidate is eligible to reach the NVT6 selector. It does **not** mean the teacher line has been selected.

`INTERNAL_ONLY` means the candidate structure may exist, but it belongs to an internal/lower-timeframe context for the current timeframe.

`UNRESOLVED` means evidence is insufficient and the selector must not silently decide ownership.

The current preflight tools intentionally produce **evidence**, not these final ownership labels.

## Features allowed in preflight experiments

Research may inspect:

- anchor provenance (`CONFIRMED_38` / `MICRO_DOW`);
- whether a candidate starts from a production-confirmed structural origin;
- nested depth / local-Dow sequence;
- elapsed bars/time;
- price displacement normalized to the enclosing production leg;
- cluster membership and right-edge rank;
- whether the candidate is entirely contained inside one active production leg;
- wick-outlier metadata;
- current timeframe and known lower-timeframe alternative evidence.

The following are prohibited as shortcuts:

- GT case ID hard-coding as runtime logic;
- lowering the 38% production threshold until a case passes;
- allowing selector score to override a valid NO-LINE ownership result;
- treating every Micro-Dow candidate as H1-owned;
- treating a structure-specific NO-LINE event as a blanket negative label for all candidates at that cutoff;
- changing production code before NVT9.

## Required gates before selector beta scoring

1. **GT_0006 recall gate**: at least one teacher-like P38_MICRO candidate exists.
2. **GT_0007 global negative gate**: recognized Micro-Dow structures must not force an H1 line when teacher evidence says H1 should have none.
3. **GT_0005 target gate**: identify the rejected apparent structure before using it as a candidate-level negative ownership example.
4. **Candidate identity gate**: duplicate/collision behavior found in GT_0003 must be audited before selector metrics are trusted.
5. **No production writeback**: all experiments stay under `tools/nvt/` / `nvt_output`.

## Recommended NVT6 order

```text
P0  Build generic research Micro-Dow pools for GT_0005/0006/0007
P1  Produce ownership evidence matrix with NO-LINE scope
P2  Audit GT_0003 candidate identity / duplicate rows
P3  Identify GT_0005 rejected-structure target from video/OHLC evidence
P4  Add selector-support metadata: cluster edge + wick outlier
P5  Only then prototype Structure Selector beta
P6  Score positive cases and correctly scoped NO-LINE negatives together
```

## Promotion guard

This document defines research work only. Even a successful ownership gate remains NVT evidence until NVT8 held-out validation and NVT9 production promotion review pass.
