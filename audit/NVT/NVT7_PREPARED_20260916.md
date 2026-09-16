# NVT7 Prepared — 2026-09-16

Status: **IMPLEMENTED / RESEARCH ONLY / AWAITING HOST EXECUTION**

## Trigger

NVT6 GT_0006 visual state-sequence analysis showed that no single fixed Gate-C geometry explains all direct video samples. This establishes material at the NVT6 selector / NVT7 lifecycle boundary, but does not by itself define a production lifecycle rule.

## NVT7 evidence set

- GT_0002: update current while retaining a useful older reference.
- GT_0004: persistent monitoring reference can be preferable to a newer PC re-anchor.
- GT_0005: structurally valid small-Dow turn line intentionally suppressed from display because it is steep/short-lived and adds clutter.
- GT_0006: same MT4 object name observed across multiple geometry samples; stable candidate matches and at least one transient/unresolved sample must be separated.

## Implemented research artifacts

- `docs/NVT/NVT7_LIFECYCLE_MODEL_BETA_RESEARCH_V01.md`
- `tools/nvt/build_nvt7_lifecycle_preflight.py`
- `tools/nvt/build_nvt7_event_state_graph.py`
- `setup/run_nvt7_lifecycle_preflight.ps1`
- `setup/RUN_NVT7_LIFECYCLE_PREFLIGHT.cmd`
- `setup/run_nvt7_prepare.ps1`
- `setup/RUN_NVT7_PREPARE.cmd`

The stale NVT1 GT_0005 registry row was also amended to the corrected valid-but-display-suppressed semantics.

## Provisional lifecycle states

Research labels only:

```text
CURRENT_ACTIVE
REFERENCE_RETAINED
VALID_SUPPRESSED
EDIT_TRANSIENT
REANCHORED_CURRENT
```

`RETIRED` / default deletion is intentionally not fixed.

## Required host input

Existing NVT6 result:

```text
%APPDATA%\MetaQuotes\Terminal\Common\Files\noda_draw\nvt_output\nvt6_visual\GT_0006_VISUAL_STATE_SEQUENCE.json
```

## Intended host output

```text
...\nvt_output\nvt7_lifecycle\NVT7_LIFECYCLE_PREFLIGHT.json
...\nvt_output\nvt7_lifecycle\NVT7_EVENT_STATE_GRAPH.json
```

## Pass meaning

A host PASS means the NVT7 research evidence basis and event/state graph were generated consistently. It does **not** freeze lifecycle beta semantics and does not authorize production promotion.

## Production boundary

Unchanged:

```text
Production Normal Run: unchanged
Production tools/live_draw semantics: unchanged
NCA_DRAW__: unchanged
MT4 production objects: unchanged
Trade authority: none
NVT0-NVT8 production writeback: prohibited
```
