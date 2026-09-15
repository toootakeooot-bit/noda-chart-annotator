# NVT6 Structure Ownership Preflight v0.1

Status: **DRAFT / RESEARCH ONLY**  
Date: 2026-09-15  
Scope: NVT-only. Production `tools/live_draw/`, Normal Run, `NCA_DRAW__`, trade state, and MT4 production objects remain unchanged.

## Purpose

GT_0006 demonstrated that the current production 38% Turn Detector can preserve the large H1 structural origin while suppressing nested small-Dow rebound highs that the teacher later uses as TL alternatives. A research-only Micro-Dow layer restored those missing alternatives without weakening the 38% detector.

However, GT_0005 and GT_0007 show that **recognizing a small-Dow structure does not automatically mean H1 should draw a line**. The teacher explicitly assigns some internal structures to a lower timeframe and expects **NO-LINE on H1**.

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

### GT_0005 / GT_0007 — H1 NO-LINE cases

Teacher evidence:
- visible internal movement exists;
- nevertheless the line should not be owned by H1;
- if a line is desired, use the lower-timeframe/internal-wave structure.

These are mandatory negative controls.

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

This hypothesis must be tested against GT_0005 / GT_0006 / GT_0007. It must not be hard-coded as production behavior.

## Ownership outputs

The experimental gate returns one of:

```text
OWNED_CANDIDATE
INTERNAL_ONLY
UNRESOLVED
```

`OWNED_CANDIDATE` means only that the candidate is eligible to reach the NVT6 selector. It does **not** mean the teacher line has been selected.

`INTERNAL_ONLY` means the structure may exist, but it belongs to an internal/lower-timeframe context for the current timeframe.

`UNRESOLVED` means evidence is insufficient and the selector must not silently decide ownership.

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
- allowing selector score to override a NO-LINE ownership result;
- treating every Micro-Dow candidate as H1-owned;
- changing production code before NVT9.

## Required gates before selector beta scoring

1. **GT_0006 recall gate**: at least one teacher-like P38_MICRO candidate exists.
2. **GT_0005 negative gate**: Micro-Dow recognition must not force an H1 line.
3. **GT_0007 negative gate**: Micro-Dow recognition must not force an H1 line.
4. **Candidate identity gate**: duplicate/collision behavior found in GT_0003 must be audited before selector metrics are trusted.
5. **No production writeback**: all experiments stay under `tools/nvt/` / `nvt_output`.

## Recommended NVT6 order

```text
P0  Build generic research Micro-Dow pools for GT_0005/0006/0007
P1  Produce ownership evidence matrix
P2  Audit GT_0003 candidate identity / duplicate rows
P3  Add selector-support metadata: cluster edge + wick outlier
P4  Only then prototype Structure Selector beta
P5  Score positive cases and NO-LINE negatives together
```

## Promotion guard

This document defines research work only. Even a successful ownership gate remains NVT evidence until NVT8 held-out validation and NVT9 production promotion review pass.
