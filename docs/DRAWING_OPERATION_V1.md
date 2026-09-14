# NODA Chart Annotator — Drawing Operation v1

Status: **FIXED**  
Fixed date: **2026-09-14**

This document fixes the operating contract beneath `docs/BOUNDARY_V1.md`.
Boundary v1 remains the top-level contract. If this document conflicts with Boundary v1, Boundary v1 takes precedence.

## 1. Supported instruments

- The drawing system shall support **all symbols available in XM MT4① in principle**.
- Do not use a per-symbol allowlist as the architectural boundary.
- Do not hard-code the system around only `GOLD#`, `USDJPY#`, `US100Cash#`, `JP225Cash#`, or any other initial subset.
- The canonical symbol identity is the **XM MT4 symbol name**, as fixed by Boundary v1.

Status: **FIXED**

## 2. Timeframes

The basic monitored timeframes are:

- `D1`
- `H4`
- `H1`
- `M15`

Status: **FIXED**

## 3. Monitoring / re-evaluation trigger

The formal term is **monitoring / re-evaluation trigger**.

For each timeframe independently, a trigger occurs when **one new closed bar is confirmed on that timeframe**.

A trigger means: observe the new confirmed-bar input and re-evaluate the drawing state.
A trigger does **not** itself mean redraw, replacement, deletion, or creation of a line.

```text
closed bar confirmed
 -> monitoring / re-evaluation trigger
 -> local NCA re-evaluation
 -> no drawing-state change
      -> do nothing
    OR
 -> valid drawing-state change
      -> update only the required managed objects
```

D1 / H4 / H1 / M15 do not need to advance together. Each timeframe triggers independently when its own new closed bar is confirmed.

Status: **FIXED**

## 4. TL / CH lifecycle

TL display retention uses the existing Lifecycle v1 semantics and keeps at most:

```text
current TL
+
immediately previous TL
```

When a third TL generation is validly established:

- the new TL becomes current,
- the prior current TL becomes previous,
- the oldest displayed TL is removed from MT4① display.

CH belongs to its parent TL generation and follows that parent lifecycle. When a TL generation is retired from display, its dependent CH is retired with it unless a more specific fixed lifecycle clause explicitly says otherwise.

A monitoring / re-evaluation trigger alone does not create a new TL generation.

Reference: `docs/LIVE_DRAW_LIFECYCLE_V1.md`.

Status: **FIXED**

## 5. Managed-object prefix and manual-object protection

All system-managed drawing objects must use the dedicated prefix:

```text
NCA_DRAW__
```

Example identities:

```text
NCA_DRAW__GOLD#_H4_TL_G003
NCA_DRAW__GOLD#_H4_CH_G003
```

The system may create, update, replace, or delete only objects that it owns under the dedicated managed prefix / identity contract.

**Objects without the system-managed prefix are user/manual objects and must not be deleted, renamed, repositioned, or otherwise modified by NCA.**

TEST-only prefixes such as `NCA_TEST__` may remain in isolated test renderers, but they are not the production managed-object prefix fixed by this contract.

Status: **FIXED**

## 6. Runtime judgment and rendering responsibility

Runtime drawing judgment belongs to **NCA local logic (currently Python)**.

```text
MT4① market data / confirmed bars
 -> NCA local logic (currently Python)
 -> drawing state / snapshot
 -> MT4① render
```

- ChatGPT is **not** part of the runtime drawing judgment path.
- ChatGPT is **not** inserted between market data and drawing output.
- MT4① is the drawing destination / renderer, not the strategy owner.
- ChatGPT may still be used outside runtime for specification review, audit, and development discussion.

Status: **FIXED**

## Fixed summary

| No. | Fixed item | Status |
|---|---|---|
| 1 | XM MT4① symbols: all available symbols supported in principle; no per-symbol allowlist/hard-code boundary | FIXED |
| 2 | Basic timeframes: D1 / H4 / H1 / M15 | FIXED |
| 3 | One new closed bar on each timeframe independently triggers monitoring / re-evaluation; trigger != redraw | FIXED |
| 4 | TL keeps current + immediately previous; third valid generation retires oldest; CH follows parent TL | FIXED |
| 5 | Production managed-object prefix = `NCA_DRAW__`; non-owned/manual objects must not be touched | FIXED |
| 6 | NCA local logic (currently Python) judges runtime drawing; ChatGPT not in runtime path; MT4① renders | FIXED |

```text
NCA DRAWING OPERATION V1
STATUS: FIXED
SYMBOLS: XM MT4① ALL SYMBOLS IN PRINCIPLE
TIMEFRAMES: D1 / H4 / H1 / M15
TRIGGER: NEW CLOSED BAR PER TIMEFRAME -> RE-EVALUATE ONLY
TL DISPLAY: CURRENT + PREVIOUS
CH: CHILD OF PARENT TL
PREFIX: NCA_DRAW__
MANUAL OBJECTS: DO NOT TOUCH
JUDGMENT: NCA LOCAL LOGIC (CURRENTLY PYTHON)
CHATGPT: NOT IN RUNTIME PATH
RENDER: MT4①
```
