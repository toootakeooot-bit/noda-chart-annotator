# NVT9 Phase-1 Tooling Advance Audit - 2026-09-20

Audit ID: ID10IQ200  
Scope: USDJPY# / 09-19 teacher comparison  
Status: RESEARCH PIPELINE PREPARED / LOCAL EVIDENCE REQUIRED

## What has been advanced

### V3.5 Cross-timeframe ownership

The review matrix now compares D1-H4, H4-H1 and H1-M15 without assuming source timeframe equals structural owner timeframe.

Evidence exported per parent/child pair includes:

- direction agreement
- projected TL and CH gaps
- slope difference
- anchor-time differences
- channel-width-normalized TL gap
- parent anchor-span hours
- child anchor-span hours
- child/parent anchor-span ratio

The remembered H1 -> H4 / H4 -> D1 issue is therefore measured explicitly, but there is still no fixed elapsed-hour threshold.

### Conservative ownership adjudication

New policy:

- EXACT_GEOMETRY_SAME_FAMILY may auto-resolve to PARENT_OWNED_SAME_FAMILY.
- Every other non-exact case defaults to AMBIGUOUS_KEEP_VISIBLE.
- Opposite direction alone does not auto-prove LOCAL_OWNED_DISTINCT.
- Metric closeness, slope closeness, or elapsed hours cannot auto-promote ownership.
- Ambiguous rows block V4 and remain visible.

Outputs are separated into:

1. AUTO adjudication
2. override TEMPLATE
3. optional explicit teacher/manual OVERRIDES
4. FINAL adjudication after validated merge
5. V3.5 gate result

A parent-owned override must reference an actual parent line present in the review matrix.

### V4 visibility decision preparation

An ownership-aware V4 decision builder is ready.

It does not automatically suppress any line. For confirmed parent-owned lines it requests a visual decision between DRAW / REFERENCE / SUPPRESSED based on whether the lower-TF representation materially improves geometry.

The old H1 16 -> 12 PREVIOUS-zone hypothesis remains secondary. If H1 is confirmed as parent-owned by H4, parent-duplication handling must be reviewed before the generic 16 -> 12 hypothesis.

### V5 regression preparation

A visibility invariant validator is ready for the eventual audit preview. It checks the frozen 09/19 H1 requirements:

- LARGE_DOW CURRENT TL retained
- LARGE_DOW CURRENT CH retained
- previous reference TL retained
- previous reference CH retained
- multiple H1 structural states can coexist
- object IDs remain unique

This is an invariant regression only; it does not prove exact teacher geometry or Production readiness.

## One-shot local runner

Use:

setup\RUN_NVT9_PHASE1_ADVANCE_0919.cmd

It performs, in order:

1. cross-TF self-test
2. live 09/19 cross-TF matrix build
3. ownership adjudication self-test
4. AUTO adjudication
5. optional explicit override merge
6. V3.5 gate evaluation
7. V4 decision-input build
8. V5 regression self-test

If V3.5 remains blocked, it stops at the correct evidence boundary and prints the generated override template path.

## Current hard blocker

Repository-side work can proceed no further to an evidence-backed V4 policy without the local MT4/live-output matrix and explicit adjudication of non-exact ownership rows.

This is intentional. The 09/19 observation:

- H4 NCA ~= teacher D1
- H1 NCA ~= teacher H4
- M15 NCA ~= teacher H1

remains an adjudication input, not a global fixed shift rule.

## Safety result

No change has been made to:

- Turn detector
- candidate generation
- Large/Mid selector
- lifecycle state
- Production Normal Run
- Production snapshot
- Renderer
- NCA_DRAW__ ownership/writeback
- MT4 drawing objects

Production promotion remains blocked.


## Additional downstream preparation completed

### Explicit V4 display decisions

After V3.5 passes, a separate display-decision template can now be generated for confirmed parent-owned line families.

Guardrails:

- ownership confirmation alone does not authorize suppression;
- H1 LARGE_DOW CURRENT TL/CH are pre-locked to DRAW from the frozen 09/19 teacher invariant;
- all other DRAW / REFERENCE / SUPPRESSED decisions require explicit visual/teacher review;
- missing decisions block the preview rather than silently defaulting to suppression.

### V6 audit-only preview

A new V6 preview builder applies only explicit per-line/per-role display decisions to a copy of the Normal Run snapshot.

It does not modify the source snapshot, Production Renderer, or NCA_DRAW__ objects. The V5 invariant validator is then run against this preview before any MT4 visual test.

### V7 isolated MT4 research preview

A separate one-shot MT4 renderer is prepared:

- source: mt4/NCA_NVT9_Preview_Renderer.mq4
- ownership prefix: NVT9_PREVIEW__
- input: NORMAL_<symbol>_live_snapshot_V6_0919.csv
- Production prefix NCA_DRAW__ is not owned or deleted
- manual objects are not owned or deleted
- no timer and no trading functions

A V7 readiness auditor blocks host rendering unless both V6 preview and V5 regression pass.

### CI verification

GitHub Actions research CI passed on commit 2af9fcd661e0463f1b1992fc4c96e0b8ec1acbc2 after correcting two audit-tool defects found by CI:

1. V6/legacy visibility CSV code referenced fieldnames on the file handle instead of the DictReader.
2. the preview-renderer safety test incorrectly rejected a harmless NCA_DRAW__ mention in a comment.

The corrected suite passes cross-TF, ownership adjudication, V4 decision, V4->V6 preview, V5 invariants, preview-renderer safety, and V7 readiness self-tests.

## Effective stop point now

Repository-side tooling is prepared through V7 readiness.

The remaining evidence-bearing work requires the user's local MT4/live data:

1. build the actual 09/19 cross-TF matrix;
2. explicitly adjudicate non-exact H4/H1/M15 ownership rows;
3. select display treatment for confirmed parent-owned lines;
4. build V6 preview and pass V5 invariants;
5. render isolated NVT9_PREVIEW__ objects in MT4 and compare screenshots.

Production promotion remains blocked throughout this research path.
