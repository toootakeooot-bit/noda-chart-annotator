# NVT8 Strict Independent Video Validation V0.1

Status: RESEARCH ONLY / PREPARED / BLOCKED UNTIL CLEAN HELD-OUT VIDEO EXISTS

## Goal

Validate the frozen NVT7 lifecycle beta and NVT7.1 USDJPY H1 semantic contract on a teacher video source that was not inspected or used during NVT0-NVT7.1 development.

This is the strict roadmap gate. NVT8-H historical user-adjudicated review remains supplemental evidence only and does not satisfy this gate.

## Frozen prerequisites

Strict NVT8 starts only when all of the following are true:

- NVT7 lifecycle scoped beta is frozen and held-out-ready.
- NVT7 frozen-scope regression passes.
- NVT7.1 semantic freeze candidate schema `nvt7.1-usdjpy-semantic-freeze-candidate/0.2` is `PASS_CONTRACTS`.
- No Production Normal Run, `NCA_DRAW__`, MT4 rendering, or trade authority writeback has occurred.
- At least one clean source-level held-out USDJPY teacher video has been registered before any teacher-event inspection.

## Current frozen NVT7.1 semantics carried into NVT8

- `LARGE_DOW_TL` is the primary drawable structural trendline.
- `TURN_LINE` is internally valid but automatically suppressed; there is currently no automatic display exception.
- Small-Dow high break changes local structure state only.
- Large-Dow promotion requires a closed-bar close above the active large-Dow high gate.
- High/gate wick-only penetration does not count as a break.
- `LAST_PULLBACK_LOW` / `PROTECTED_LOW` break requires a closed-bar close below the level; wick-only penetration does not count.
- 38% retrace and protected-low break remain separate evidence fields; both true gives strong structural-high confirmation.
- The universal deterministic SMALL/MID/LARGE Dow-scale classifier remains deliberately unfixed and must not be invented during NVT8.

## Source-level holdout policy

A source is clean only if it was not previously inspected, registered, summarized, or used as development evidence in NVT0-NVT7.1.

The current five-video teacher corpus is not clean for strict NVT8 because all five sources were touched during development. Therefore a new unseen teacher video is required.

The held-out source must be registered before teacher-event review begins using `nvt/manifests/NVT8_HELD_OUT_SOURCE_REGISTRATION_TEMPLATE.json` or an equivalent frozen record.

## Validation sequence

```text
register unseen source before review
        ↓
freeze source identity / eligibility
        ↓
extract teacher events without tuning
        ↓
time-freeze broker OHLC at each event
        ↓
run frozen NVT candidate / selector / lifecycle / semantic rules
        ↓
compare against teacher by failure layer
        ↓
produce held-out metric report + unresolved limitations
        ↓
NVT8 promotion recommendation or rejection
```

No rule tuning is permitted after held-out teacher inspection begins. A failure is evidence to report, not permission to patch the frozen rule and rerun the same source as if it remained held-out.

## Failure layers

Use the fixed diagnostic order where applicable:

`STRUCTURE_SCALE_MATCH → CANDIDATE_PRESENT → ANCHOR_MATCH → SELECTOR_MATCH → NO_LINE_MATCH`

Lifecycle and semantic-state disagreements must be reported separately, including at minimum:

- line role (`LARGE_DOW_TL` / `TURN_LINE`),
- visibility (`DRAW` / `VALID_SUPPRESSED`),
- local vs parent Dow promotion state,
- structural-high evidence state,
- keep / replace / reference-retention lifecycle result.

## Gate result

Strict NVT8 may end in promotion recommendation or rejection. Neither result writes Production directly. Production changes remain NVT9-only and responsibility-layer based.

## Current state

The expected current preflight result is:

`BLOCKED_NO_CLEAN_SOURCE_LEVEL_HOLDOUT`

when NVT7 and NVT7.1 prerequisites pass but no new unseen teacher video has been registered.

This BLOCKED status is a correct research gate, not a runner failure.
