# NVT5 GT_0006 Micro-Dow Prototype Result — 2026-09-15

Status: **RESEARCH PASS / NOT PRODUCTION**

## Scope

Case: `GT_0006`, USDJPY H1, source `NVT_VIDEO_20260912`.

This audit records the result of the research-only `MICRO_DOW` prototype. Production `tools/live_draw`, Normal Run, `NCA_DRAW__`, MT4 objects, and trade state remain unchanged.

## Input result

Prototype schema: `nvt-micro-dow-prototype/0.1`.

Rules used:
- production 38% detector unchanged;
- micro HIGH confirmation = `LOW -> rebound HIGH -> LOWER LOW`;
- strict noise filter requires L2/R2 local-extrema status;
- no automatic teacher-line selection;
- no production writeback.

## Counts

- production-confirmed anchor1 count: 1
- strict micro anchor1 count: 4
- strict micro anchor2 count: 12
- falling micro pair count: 48
- falling pairs from the production-confirmed anchor1: 12

## Primary finding

The prior GT_0006 `ABSENT` result was a candidate-recall / structure-scale gap rather than a selector-only problem.

Adding a separate nested Micro-Dow layer restores teacher-like descending TL alternatives **without weakening the production 38% detector**.

Most importantly, the production-confirmed major HIGH at `2026-09-02T04:00:00` / `160.387` can remain the primary structural origin while 12 strict Micro-Dow highs supply alternative second anchors. This supports a hybrid candidate architecture:

`CONFIRMED_38 primary anchor -> MICRO_DOW secondary anchor`

before considering unrestricted `MICRO -> MICRO` promotion.

## Teacher-preference alignment hypothesis

From the production-confirmed anchor1, the gentlest second-anchor alternatives are clustered on 2026-09-11:

- 2026-09-11 15:00 / 154.480 / |slope| ~= 0.026022 per hour
- 2026-09-11 11:00 / 154.367 / |slope| ~= 0.026996 per hour
- 2026-09-11 02:00 / 154.609 / |slope| ~= 0.027000 per hour

This is directionally consistent with GT_0006 teacher evidence: preserve multiple valid cluster-edge candidates and prefer a gentler line.

However, the prototype does **not** prove which pair is the teacher's exact line. In particular the teacher also discusses excluding an unusually long wick as possible noise. Therefore wick/outlier handling must be feature metadata / penalty, not a hard pre-delete.

## Strong design candidate

Preferred next research architecture:

1. Keep current `CONFIRMED_38` pivots unchanged for large/mid structural origins.
2. Add `MICRO_DOW` pivots as a separate nested layer.
3. First test a constrained hybrid pool where an H1 TL has a production-confirmed H1 primary anchor and a structurally-confirmed Micro-Dow secondary anchor.
4. Treat fully `MICRO -> MICRO` lines as internal-structure candidates until timeframe/structure ownership is proven.
5. Apply a Structure Ownership / NO-LINE gate before selection so GT_0005 and GT_0007 remain valid zero-H1-line cases.
6. Score cluster-edge position, gentler slope, pullback coverage, wick-outlier metadata, and structural validity only after candidate recall is secured.

## Why this matters for GT_0005 / GT_0007

GT_0005 and GT_0007 explicitly show that an internal wave can belong to a lower timeframe and that H1 may correctly output no line. Therefore recovering Micro-Dow pivots must not imply drawing every recovered H1 micro line.

A promising ownership hypothesis to test is:

- `CONFIRMED_38 -> MICRO_DOW` may represent an H1-owned line candidate;
- `MICRO_DOW -> MICRO_DOW` wholly inside one production leg may be an internal/lower-timeframe candidate and may require NO-LINE on H1.

This is a hypothesis only and requires negative-case validation before NVT6 scoring.

## Remaining gates before NVT6 selector work

- Validate Structure Ownership against GT_0005 and GT_0007.
- Audit GT_0003 duplicate candidate identity / conflicting structural metrics.
- Do not auto-select the teacher line from GT_0006 yet.
- Keep production 38% logic untouched until NVT8/NVT9 promotion criteria are satisfied.

## Verdict

**Micro-Dow candidate recall: PASS for GT_0006 research objective.**

The result supports adding a separate nested structural layer, not reducing the 38% threshold globally.
