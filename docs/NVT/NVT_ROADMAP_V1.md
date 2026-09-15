# NVT Roadmap v1

Status: **FIXED**  
Fixed date: 2026-09-15

This roadmap fixes the development order for NVT v1. The order may only be changed by an explicit revision/audit decision.

## NVT0 — Boundary / Ground Truth definition

Goal: establish the research boundary before implementation.

Deliverables:

- `NVT_BOUNDARY_V1.md`
- `GROUND_TRUTH_SCHEMA_V1.md`
- `VALIDATION_RULES_V1.md`
- `NVT_ROADMAP_V1.md`
- materials checklist
- repository scaffold

Gate:

```text
Boundary fixed
Ground Truth fields fixed
Time-freeze rule fixed
NVT0-NVT8 production protection fixed
```

## NVT1 — Static-image case registration

Goal: register still-image reference cases without changing production NCA.

Deliverables:

- DRAFT Ground Truth JSON cases;
- source manifests;
- annotation notes/confidence;
- initial teacher-object inventory.

Primary questions:

- Which lines are actually visible?
- Which anchors can be identified confidently?
- Which role/style distinctions recur?

Gate: enough reviewed still cases to exercise candidate comparison.

## NVT2 — Candidate Dump

Goal: expose NCA's full candidate pool at each frozen case time.

Deliverables:

- `tools/nvt/dump_candidates.py`;
- machine-readable candidate dump;
- anchor/contact/geometry metadata.

Gate: for every static case, determine whether the teacher line exists in the candidate pool.

## NVT3 — Teacher-NCA Diff

Goal: classify why NCA differs from teacher evidence.

Deliverables:

- comparison engine;
- per-case diff report;
- failure taxonomy totals;
- first Candidate Recall / Selection / Anchor / Channel metrics.

Gate: differences are attributed to layers rather than treated as visual mismatch only.

## NVT4 — Video Event extraction

Goal: convert video changes into ordered teacher actions.

Deliverables:

- event manifest;
- frame/timestamp references;
- ADD/KEEP/MOVE/REPLACE/DELETE event records;
- teacher-stated rationale kept separate from analyst inference.

Gate: repeatable extraction of structural drawing events from source videos.

## NVT5 — Time-Frozen Replay

Goal: reproduce each teacher event using only data available at that event time.

Deliverables:

- `replay_to_time.py`;
- frozen OHLC inputs/cutoffs;
- replay outputs linked to Ground Truth;
- look-ahead guard checks.

Gate: deterministic teacher-vs-NCA comparison at historical decision points.

## NVT6 — Structure Selector beta

Goal: derive reproducible local rules for choosing among existing candidates.

Rules:

- do not patch selector when teacher candidate is absent;
- preserve production baseline separately;
- selector runs locally/deterministically;
- no ChatGPT runtime dependency.

Deliverables:

- experimental selector under `tools/nvt/`;
- scored comparisons against baseline;
- rule provenance back to Ground Truth cases.

Gate: demonstrable improvement on development cases without degrading core candidate validity.

## NVT7 — Lifecycle Model beta

Goal: model teacher keep/replace/delete behavior and structural role persistence.

Potential states may be explored, but are not fixed in advance. Evidence must decide whether distinctions such as major/current/reference are required.

Deliverables:

- experimental lifecycle model;
- sequential event regression;
- explicit treatment of retained old-but-valid structures.

Gate: improved lifecycle accuracy on video cases.

## NVT8 — Independent video validation

Goal: test the frozen NVT beta rules on held-out source material not used to tune them.

Deliverables:

- held-out validation set;
- metric report by failure layer;
- regressions against current NCA baseline;
- unresolved limitations.

Gate: explicit promotion recommendation or rejection.

## NVT9 — NCA Production Promotion

Goal: promote only validated rules into production NCA.

Only at NVT9 may production `tools/live_draw/`, production selection/lifecycle semantics, or production rendering behavior be changed because of NVT findings.

Promotion procedure:

```text
validated NVT rule
 -> production design review
 -> NCA implementation branch
 -> regression against existing NR baselines
 -> MT4 verification
 -> production FIXED documentation update
```

Experimental names such as `Teacher Selector` should normally be converted to neutral production names such as `Structure Selector` when promoted.

## Fixed order

```text
NVT0  Boundary / Ground Truth
NVT1  Static image cases
NVT2  Candidate Dump
NVT3  Teacher-NCA Diff
NVT4  Video Event extraction
NVT5  Time-Frozen Replay
NVT6  Structure Selector beta
NVT7  Lifecycle Model beta
NVT8  Independent video Validation
NVT9  NCA Production Promotion
```
