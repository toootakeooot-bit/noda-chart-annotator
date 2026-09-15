# NVT Boundary v1

Status: **FIXED**  
Fixed date: 2026-09-15  
Repository: `toootakeooot-bit/noda-chart-annotator`  
Development branch: `feature/nvt-validation-v1`

## 1. Purpose

NVT = **NODA Visual Teacher**.

NVT is the research / validation area used to analyze reference images and videos from Noda-sensei, convert observed drawing behavior into structured Ground Truth, compare it against NCA, and derive reproducible local drawing rules.

NVT exists to improve **what NCA chooses to draw and retain**, not to replace the NCA runtime architecture.

## 2. Relationship to NCA

- NCA remains the production chart-annotation system.
- Current Normal Run / TL / CH behavior remains the baseline during NVT0-NVT8.
- `tools/live_draw/` is production logic and is not modified merely because an NVT experiment looks better.
- NVT experimental code lives under `tools/nvt/` and NVT evidence/data lives under `nvt/`.
- Production promotion occurs only at NVT9 after validation gates pass.

## 3. Production-protection rule

**NVT0-NVT8 must not change production NCA drawing semantics.**

Changes to production `tools/live_draw/`, production snapshot semantics, or `NCA_DRAW__` behavior require NVT9 promotion and an explicit audit decision.

Experimental MT4 objects, when added later, must use a separate ownership prefix such as:

```text
NCA_NVT__
```

They must not delete, rename, move, or modify `NCA_DRAW__` or user/manual objects.

## 4. Source evidence policy

Reference screenshots and videos are evidence sources, not runtime dependencies.

NVT runtime research outputs must be converted into structured records such as:

- Ground Truth cases;
- event manifests;
- candidate dumps;
- comparison reports;
- scoring / validation reports.

Large original image/video assets should not be committed to GitHub by default. They may remain on the user's PC / Drive / other controlled storage, with NVT manifests recording source identifiers and timestamps.

## 5. Time-frozen validation rule

When reproducing a teacher decision at time T, NCA/NVT may use only market data available up to T.

Future bars after T must not be visible to the replay used for that Ground Truth decision.

This rule is mandatory to prevent look-ahead bias.

## 6. Separation of concerns

NVT must distinguish at least these failure classes:

```text
CANDIDATE_ABSENT
SELECTION
ANCHOR
CHANNEL
LIFECYCLE
ROLE
RENDER_STYLE
```

Candidate generation, selection, lifecycle, and rendering must not be treated as one undifferentiated problem.

## 7. Runtime boundary unchanged

NVT does not introduce:

- TC dependency;
- ChatGPT runtime dependency;
- NODA Engine write-back;
- trade execution;
- order / SL / TP / lot / ticket authority.

The intended production path remains local and deterministic after promotion.

## 8. Authority

For NVT v1 research, this document and the associated Ground Truth / Validation / Roadmap documents are the controlling NVT contract.

Any change to this boundary requires an explicit NVT revision rather than an ad-hoc code change.
