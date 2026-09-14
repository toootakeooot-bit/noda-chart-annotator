# Boundary v1 Audit — 2026-09-14

## Result

**PASS — FIXED**

## Scope fixed by owner approval

The following NCA top-level boundaries are fixed:

- Purpose: draw lines/arrows on MT4①.
- Target MT4: MT4① only.
- Canonical symbol naming: XM MT4 symbol names.
- TC: unused, no dependency, no future integration planned.
- TC consumption: out of scope.
- Market hours: not used as a judgment/execution condition.
- NODA Engine: separate system; no integration.
- Trade execution: none; no order/close/modify/SL/TP-change authority.
- Drawing targets: TL / HL / CH / direction arrow.
- Judgment owner: ChatGPT judges; MT4① renders instructions.

Canonical contract: `docs/BOUNDARY_V1.md`.

## Conflict audit against previous Live Draw baseline

The previous `docs/LIVE_DRAW_BASELINE_V1.md` contained statements that conflict with Boundary v1, notably:

1. non-XM canonical symbols (`USDJPY`, `GOLD`, `US100`) with XM names treated only as broker mappings;
2. HL placed on HOLD and Zones included as primary v1 drawing outputs;
3. an M15-close cadence presented as the initial Live Pipeline schedule;
4. a detector-centric wording that can be read as assigning judgment to the local Live Draw pipeline rather than ChatGPT.

Resolution:

- `docs/BOUNDARY_V1.md` is the higher-precedence boundary contract;
- older technical documents remain valid only where they do not conflict with Boundary v1;
- conflicting technical details require later redesign/review before implementation is treated as Boundary-compliant.

## Non-scope deliberately not fixed here

Boundary v1 does **not** yet fix:

- exact update/refresh trigger;
- timeframe set used for judgment;
- object naming/prefix convention;
- line replacement/deletion/history rules;
- exact arrow semantics;
- exact TL/HL/CH detection rules;
- MT4 transport format from ChatGPT judgment to renderer.

These are implementation/specification items to be fixed separately.

## Declaration

```text
BOUNDARY_V1_AUDIT = PASS
BOUNDARY_V1_STATUS = FIXED
OLDER_CONFLICTING_CLAUSES = SUBORDINATE
```
