# NVT9 09/19 Cross-TF Root-Cause Audit

Audit ID: ID10IQ200  
Date: 2026-09-20  
Status: ROOT CAUSE IDENTIFIED / PRODUCTION UNCHANGED

## Trigger

The first V3.5 live matrix produced six AMBIGUOUS_KEEP_VISIBLE rows:

- H4 current lines were FALLING and were hypothesized by the user to belong to teacher D1.
- H1 current lines were FALLING and were hypothesized to belong to teacher H4.
- M15 current lines were RISING and were hypothesized to belong to teacher H1.

The initial implementation treated this mainly as a structural-owner / parent-family matching problem.

## Root cause found

The Production Normal Run exporter uses one fixed input horizon for every timeframe:

```
BarsToExport = 600
```

Therefore the approximate calendar coverage is radically different by timeframe:

- D1: hundreds of trading days / multi-year context
- H4: roughly several months
- H1: roughly several weeks
- M15: roughly several trading days

That produces a relative-structure scale shift. A "Large" structure inside a 600-bar lower-timeframe window can correspond visually to what the teacher draws on the next higher chart.

This matches the user's 09/19 observation pattern:

- NCA H4 ~ teacher D1
- NCA H1 ~ teacher H4
- NCA M15 ~ teacher H1

## Evidence from the first live V3.5 matrix

The first live state contained:

- H4 LARGE: FALLING, 2026-07-23 -> 2026-09-02
- H1 LARGE: FALLING, 2026-08-18 -> 2026-09-02
- M15 LARGE: RISING, 2026-09-10 -> 2026-09-17

These are progressively shorter calendar structures as the source timeframe falls.

## Evidence from frozen strict NVT8 deep-history replay

The held-out strict replay used deep NVT history and selected much broader current structures at the same 09/18 cutoff:

- H4 LARGE: RISING, 2025-05-22 -> 2026-09-08
- H1 LARGE: RISING, 2025-10-01 -> 2026-09-08
- H1 MID: RISING, 2025-10-30 -> 2026-09-08

The H1 teacher-required retained/current structure is therefore not even representable from a 600-H1-bar window extending only a few weeks.

## Consequence

The first V3.5 matrix must not be used to freeze H4->D1 / H1->H4 / M15->H1 as a semantic ownership rule.

Before owner adjudication, the research comparison must use a deep-history input whose horizon is sufficient to reproduce the strict held-out selector context.

## Implemented correction

The V3.5 research runner now:

1. keeps Production Normal Run untouched;
2. reads the existing Production live state only as an audit comparator;
3. requires NVT deep-history input from `nvt_input`;
4. compares the 600-bar live current geometry against direct deep-history selection;
5. builds a RESEARCH-ONLY full-history current state;
6. runs cross-TF ownership review from that research state;
7. performs no Production state/snapshot/Renderer/NCA_DRAW__ writeback.

If NVT deep-history files are missing, the runner stops and instructs the host to run `NCA_NVT_HistoryExporter` with `BarsToExport=6000`.

## Ownership schema correction

Structural owner and NCA parent-family match are now separate dimensions.

A teacher/manual review may confirm a higher structural owner while the current NCA parent family is still unresolved:

```
HIGHER_TF_OWNER_PARENT_UNRESOLVED
```

Such a line remains visible and cannot be suppressed until parent recall/match is resolved.

## Production safety

No Production change has been made to:

- NCA_NormalRun_Exporter
- Normal Run selector
- lifecycle
- live state
- source snapshot
- Production Renderer
- NCA_DRAW__ objects
- trade authority

The next valid evidence step is to rerun Phase-1 using the deep NVT history path.


## Second finding from the uploaded deep-history review bundle

The deep-history rerun corrected the first horizon problem:

- all 8 published Normal Run CURRENT structures differed from direct deep-history CURRENT selection;
- deep H4 changed from short FALLING structures to broad RISING structures;
- deep H1 changed from short FALLING structures to broad RISING structures;
- deep H1 LARGE exactly reproduces the frozen teacher-required H1 current geometry
  (2025-10-01 00:00 -> 2026-09-08 05:00, RISING, CH offset 5.974174114209177);
- deep M15 CURRENT is FALLING while deep H1 CURRENT is RISING.

This invalidates treating the original one-step timeframe-shift observation as an active owner rule.

However, the first deep-history V3.5 matrix still compared child CURRENT only against parent CURRENT. That is insufficient under the already-frozen NVT8 lifecycle semantics, because useful parent/reference structures may remain visible as PREVIOUS while a newer local CURRENT structure exists.

This matters directly for M15: a FALLING M15 CURRENT may correspond to a retained FALLING H1 PREVIOUS even when H1 CURRENT is RISING. A current-only parent matrix would falsely report opposite-direction evidence.

## Second correction

V3.5 now builds a deep lifecycle state with CURRENT + PREVIOUS and requires lifecycle CURRENT to match direct full-history CURRENT before the matrix is accepted.

Cross-TF comparison scope is now:

- child: CURRENT only;
- parent: CURRENT + PREVIOUS retained references.

The old H4->D1 / H1->H4 / M15->H1 shift is retained only as pre-deep-history historical evidence.

No Production behavior is changed.
