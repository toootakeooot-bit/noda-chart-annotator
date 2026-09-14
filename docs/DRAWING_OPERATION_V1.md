# NODA Chart Annotator — Drawing Operation v1

Status: **FIXED**  
Fixed date: **2026-09-14**  
Revision: **NORMAL RUN / HISTORY REBUILD FIXED**

This document fixes the operating contract beneath `docs/BOUNDARY_V1.md`.
Boundary v1 remains the top-level contract. If this document conflicts with Boundary v1, Boundary v1 takes precedence.

## 1. Supported instruments

- The drawing system shall support **all symbols available in XM MT4① in principle**.
- Do not use a per-symbol allowlist as the architectural boundary.
- Do not hard-code the system around only `GOLD#`, `USDJPY#`, `US100Cash#`, `JP225Cash#`, or any other initial subset.
- The canonical symbol identity is the **XM MT4 symbol name**, as fixed by Boundary v1.

Status: **FIXED**

## 2. Timeframes

The basic timeframes are:

- `D1`
- `H4`
- `H1`
- `M15`

Status: **FIXED**

## 3. Normal Run

NCA standard operation is **user-initiated Normal Run**.

Normal Run is not continuous monitoring and is not periodic polling. The user runs NCA when the target symbol is to be viewed / refreshed.

At Normal Run, NCA shall obtain closed-bar history for the target XM symbol on `D1 / H4 / H1 / M15`, rebuild structure from historical closed bars through the current point, determine the resulting drawing state, validate the new snapshot, and only then replace managed MT4① objects.

```text
USER NORMAL RUN
 -> acquire D1 / H4 / H1 / M15 closed-bar history
 -> rebuild structure chronologically from past to present
 -> determine current / previous
 -> build snapshot
 -> validate snapshot
 -> PASS: replace only required NCA_DRAW__ objects
 -> FAIL: keep the last valid MT4① drawing unchanged
```

The former rule "one newly closed bar automatically triggers monitoring / re-evaluation" is superseded by this Normal Run contract.

Normal operation therefore includes **no**:

- continuous monitoring,
- closed-bar-triggered automatic run,
- periodic polling,
- schedule-based automatic re-evaluation.

Status: **FIXED**

## 4. History rebuild and current / previous definition

Normal Run must rebuild TL generations **chronologically from closed-bar history**. It must not treat the TL saved by the prior execution as automatically equal to the true immediately previous market structure.

### `current`

`current` is the current valid TL generation obtained from the closed-bar history rebuild performed by the present Normal Run.

### `previous`

`previous` is formally defined as:

> **the valid TL generation that was established immediately before `current`, as determined by chronological reconstruction of closed-bar history during the present Normal Run.**

Example:

```text
actual reconstructed sequence:
TL002 -> TL003 -> TL004

Normal Run display result:
previous = TL003
current  = TL004
```

Even if the previous NCA execution ended while `TL002` was current, a later Normal Run must reconstruct the intervening generations and must not simply display `TL002 + TL004` when `TL003` is the true immediate previous generation.

If the available history cannot establish a previous generation, displaying `current` alone is valid. The run must not fabricate a previous TL.

Status: **FIXED**

## 5. TL / CH display lifecycle

The maximum displayed TL generations remain:

```text
current TL
+
immediately previous TL
```

CH is a child of its parent TL generation. Therefore, when both `current` and `previous` TL generations exist, each generation may carry its corresponding CH according to the active drawing logic.

The display-generation principle in `docs/LIVE_DRAW_LIFECYCLE_V1.md` remains valid, but for Normal Run the identity of `current` and `previous` is determined by the present history rebuild, not by blindly inheriting persisted runtime slots from the prior run.

Status: **FIXED**

## 6. Safe replacement and manual-object protection

Normal Run must **not delete existing managed drawings before the new drawing state is successfully rebuilt and validated**.

Required sequence:

```text
acquire history
 -> rebuild
 -> determine current / previous
 -> generate snapshot
 -> snapshot validation PASS
 -> replace target NCA_DRAW__ managed objects
```

If history acquisition, rebuild, snapshot generation, or validation fails, the last valid drawing currently shown on MT4① must remain intact.

All production system-managed drawing objects must use the dedicated prefix:

```text
NCA_DRAW__
```

Example identities:

```text
NCA_DRAW__GOLD#_H4_TL_G003
NCA_DRAW__GOLD#_H4_CH_G003
```

The system may create, update, replace, or delete only objects it owns under the `NCA_DRAW__` identity contract.

**Objects without the system-managed prefix are user/manual objects and must not be deleted, renamed, repositioned, or otherwise modified by NCA.**

TEST-only prefixes such as `NCA_TEST__` may remain in isolated test renderers, but they are not the production managed-object prefix fixed by this contract.

Status: **FIXED**

## 7. Runtime judgment and rendering responsibility

Runtime drawing judgment belongs to **NCA local logic (currently Python)**.

```text
MT4① closed-bar history
 -> NCA local logic (currently Python)
 -> reconstructed drawing state / snapshot
 -> MT4① render
```

- ChatGPT is **not** part of the runtime drawing judgment path.
- ChatGPT is **not** inserted between market data and drawing output.
- MT4① is the drawing destination / renderer, not the strategy owner.
- ChatGPT may still be used outside runtime for specification review, audit, and development discussion.

Status: **FIXED**

## 8. Existing fixed boundaries retained

The following remain unchanged:

- XM MT4① symbols are supported in principle without a per-symbol allowlist/hard-code boundary.
- Basic timeframes are `D1 / H4 / H1 / M15`.
- Production managed-object prefix is `NCA_DRAW__`.
- Runtime judgment stays in NCA local logic (currently Python).
- ChatGPT is not in the runtime path.
- MT4① is the drawing destination.
- TC is not used and is not a dependency.
- NODA Engine remains separate.
- No trade execution authority is introduced.

## Fixed summary

| No. | Fixed item | Status |
|---|---|---|
| 1 | XM MT4① symbols: all available symbols supported in principle; no per-symbol allowlist/hard-code boundary | FIXED |
| 2 | Basic timeframes: D1 / H4 / H1 / M15 | FIXED |
| 3 | Trigger = user-initiated Normal Run; no continuous monitoring or periodic polling | FIXED |
| 4 | Normal Run rebuilds TL generations chronologically from closed-bar history | FIXED |
| 5 | `current` and true immediate `previous` are determined by that rebuild; display maximum = current + previous; CH follows each parent TL generation | FIXED |
| 6 | Production prefix = `NCA_DRAW__`; rebuild/validate first, replace only after PASS; manual objects must not be touched | FIXED |
| 7 | NCA local logic (currently Python) judges runtime drawing; ChatGPT not in runtime path; MT4① renders | FIXED |

```text
NCA NORMAL RUN
STATUS: FIXED
TRIGGER: USER NORMAL RUN
MONITORING: NONE
PERIODIC POLLING: NONE
HISTORY REBUILD: REQUIRED
CURRENT: REBUILT FROM CLOSED-BAR HISTORY
PREVIOUS: TRUE IMMEDIATE PREVIOUS TL REBUILT FROM HISTORY
DISPLAY: CURRENT + PREVIOUS
CH: CHILD OF EACH TL GENERATION
PREFIX: NCA_DRAW__
SAFE REPLACE: REBUILD/VALIDATE FIRST, REPLACE AFTER PASS
JUDGMENT: NCA LOCAL LOGIC (CURRENTLY PYTHON)
CHATGPT: NOT IN RUNTIME PATH
RENDER: MT4①
```
