# NVT0 Bootstrap Audit — 2026-09-15

Status: **PASS / NVT0 STRUCTURE + PLANNING FIXED**

Repository: `toootakeooot-bit/noda-chart-annotator`  
Branch: `feature/nvt-validation-v1`

## 1. Purpose

Create an isolated NODA Visual Teacher (NVT) research/validation area inside the existing NCA repository without modifying current production Normal Run / TL / CH semantics.

## 2. Branch isolation

`feature/nvt-validation-v1` was created from the current `feature/normal-run-v1` baseline.

Production-oriented Normal Run development remains on its existing branch. NVT research proceeds independently.

## 3. Fixed NVT v1 control documents

Created:

```text
docs/NVT/NVT_BOUNDARY_V1.md
docs/NVT/GROUND_TRUTH_SCHEMA_V1.md
docs/NVT/VALIDATION_RULES_V1.md
docs/NVT/NVT_ROADMAP_V1.md
docs/NVT/MATERIALS_CHECKLIST_V1.md
```

These fix:

- NVT purpose and production boundary;
- structured Ground Truth fields;
- mandatory time-frozen replay/no-look-ahead rule;
- layer-specific failure taxonomy;
- NVT0-NVT9 development order;
- source-material intake requirements.

## 4. Repository scaffold created

```text
tools/nvt/
  README.md
  extract_event.py
  replay_to_time.py
  dump_candidates.py
  compare_teacher.py
  scoring.py

nvt/
  README.md
  ground_truth/GT_TEMPLATE.json
  manifests/README.md
  reports/README.md
  cases/README.md

audit/NVT/
  NVT0_BOOTSTRAP_AUDIT_20260915.md
```

The Python files are intentional non-functional placeholders reserving stage ownership. No production behavior is introduced by them.

## 5. Production protection

NVT0-NVT8 are research/validation stages only.

NVT findings must not change production `tools/live_draw/`, production snapshot semantics, or `NCA_DRAW__` behavior before NVT9 promotion.

If MT4-side experimental rendering is later added, it must use a distinct ownership prefix such as:

```text
NCA_NVT__
```

## 6. Fixed roadmap

```text
NVT0  Boundary / Ground Truth definition
NVT1  Static-image case registration
NVT2  Candidate Dump
NVT3  Teacher-NCA Diff
NVT4  Video Event extraction
NVT5  Time-Frozen Replay
NVT6  Structure Selector beta
NVT7  Lifecycle Model beta
NVT8  Independent video Validation
NVT9  NCA Production Promotion
```

This order is fixed for NVT v1 unless explicitly revised and audited.

## 7. NVT0 completion judgment

```text
BRANCH ISOLATION: PASS
NVT BOUNDARY: FIXED
GROUND TRUTH SCHEMA: FIXED
VALIDATION RULES: FIXED
ROADMAP NVT0-NVT9: FIXED
MATERIALS CHECKLIST: FIXED
REPO SCAFFOLD: CREATED
PRODUCTION NCA MODIFIED BY NVT: NO
NVT0 STATUS: PASS
NEXT STAGE: NVT1 STATIC-IMAGE CASE REGISTRATION
```

## 8. Required next evidence

NVT1 can begin when reference material is supplied with enough metadata to identify at minimum:

- source identity;
- symbol;
- timeframe;
- approximate decision/chart date;
- original or sufficiently high-resolution image/video source.

The current comparison screenshots can become DRAFT cases after those metadata fields are confirmed.
