# NVT Integration / Production Promotion Policy v1

Status: **FIXED**  
Fixed date: **2026-09-15**  
Repository: `toootakeooot-bit/noda-chart-annotator`  
Development branch: `feature/nvt-validation-v1`

This policy fixes how NVT research may eventually be introduced into production NCA. It supplements `NVT_BOUNDARY_V1.md`, `VALIDATION_RULES_V1.md`, and `NVT_ROADMAP_V1.md` without changing the production Normal Run contract.

## 1. Baseline preservation

The current production Normal Run path remains the reference baseline during NVT0-NVT8.

```text
MT4 closed-bar history
 -> current NCA Market Facts / Turn logic
 -> current Candidate Generator
 -> current Structure selection
 -> current Lifecycle
 -> snapshot validation
 -> MT4 Renderer
 -> NCA_DRAW__
```

The baseline is not discarded merely because an NVT experiment looks better.

At NVT9, the baseline implementation shall remain available as a regression reference and initial rollback target until the promoted NVT-derived implementation has passed production regression and MT4 verification.

## 2. Layer-by-layer promotion

NVT findings shall be promoted by responsibility layer, not by wholesale replacement.

Promotion layers are:

```text
A. Market Facts / Turn recognition
B. Structure ownership / Candidate generation
C. Structure Selector
D. Lifecycle / display role
E. Renderer / style
```

If a layer already matches teacher evidence adequately, NVT shall not rewrite it merely to make the architecture uniform.

Example:

```text
Market Facts          keep baseline
Candidate Generator   keep baseline
Selector              promote validated NVT rule
Lifecycle             promote validated NVT rule
Renderer              keep baseline
```

is a valid NVT9 result.

## 3. Diagnostic order is mandatory

Before changing a later layer, the earlier failure layer must be known.

```text
STRUCTURE_SCALE_MATCH
 -> CANDIDATE_PRESENT
 -> ANCHOR_MATCH
 -> SELECTOR_MATCH
 -> CHANNEL_MATCH
 -> NO_LINE_MATCH
 -> LIFECYCLE_ROLE_MATCH
 -> RENDER_STYLE
```

A `CANDIDATE_ABSENT` failure must not be hidden by Selector scoring. A wrong structural scale must not be hidden by Candidate or Lifecycle tuning.

## 4. Experimental isolation

During NVT0-NVT8:

- experimental code stays under `tools/nvt/` and related NVT-only paths;
- production `tools/live_draw/` semantics remain unchanged;
- experimental MT4 objects, if rendered, use `NCA_NVT__`;
- production objects remain owned by `NCA_DRAW__`;
- NVT must not delete, move, rename, or modify production/manual objects.

## 5. Promotion gate

No NVT-derived behavior may be promoted to production before all applicable gates pass:

```text
1. Ground Truth evidence is REVIEWED / LOCKED for the promoted behavior.
2. Time-frozen replay confirms no look-ahead use.
3. Failure layer is identified, not inferred only from pixel appearance.
4. Development-case metrics improve in the intended layer.
5. NVT8 held-out video/case validation shows the improvement generalizes.
6. Existing NR regression baselines pass.
7. MT4 actual rendering verification passes.
8. Safe replacement / manual-object protection remains intact.
```

No arbitrary single aggregate score is sufficient for promotion.

## 6. Version and rollback policy

Promoted decision logic shall carry an explicit version identity.

Initial naming convention:

```text
BASELINE_V1
NVT_V1
```

Production-neutral component names are preferred after promotion, e.g. `Structure Selector`, not `Teacher Selector`.

The first promoted NVT production version shall retain the baseline path or an equivalent reproducible baseline artifact long enough to support regression comparison and rollback.

## 7. Runtime boundary after promotion

Promotion does not change the runtime boundary:

```text
MT4 history
 -> NCA local deterministic logic
 -> validated snapshot
 -> MT4 render
```

Reference videos, ChatGPT, and NVT research artifacts are development evidence only and are not runtime dependencies.

## 8. Existing Normal Run safety contract remains authoritative

NVT promotion shall preserve:

- user-initiated Normal Run;
- no continuous monitoring / periodic polling;
- D1 / H4 / H1 / M15 history rebuild;
- safe snapshot validation before replacement;
- `NCA_DRAW__` production ownership;
- manual-object protection;
- no trade execution authority;
- no TC dependency;
- no NODA Engine write-back;
- no ChatGPT runtime dependency.

## Fixed summary

```text
CURRENT NORMAL RUN: PRESERVE AS BASELINE
NVT0-NVT8 PRODUCTION CHANGE: PROHIBITED
PROMOTION STAGE: NVT9 ONLY
PROMOTION UNIT: RESPONSIBILITY LAYER, NOT WHOLE-SYSTEM REWRITE
CANDIDATE_ABSENT: MUST NOT BE HIDDEN BY SELECTOR
HELD-OUT VALIDATION: REQUIRED
NR REGRESSION: REQUIRED
MT4 VERIFICATION: REQUIRED
BASELINE/ROLLBACK: RETAIN THROUGH INITIAL PROMOTION
EXPERIMENT PREFIX: NCA_NVT__
PRODUCTION PREFIX: NCA_DRAW__
RUNTIME: LOCAL / DETERMINISTIC
```
