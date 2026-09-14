# NCA Live Draw Baseline v1

Status: **FIXED / SUBORDINATE TO BOUNDARY V1**

> **Boundary precedence notice (2026-09-14):** `docs/BOUNDARY_V1.md` is now the top-level NCA boundary contract. Where this older Live Draw Baseline conflicts with Boundary v1, **Boundary v1 takes precedence**. In particular, Boundary v1 controls the MT4①-only target, XM MT4 canonical symbol names, TC non-use/no-dependency/no-future-plan, market-hours non-gating, NODA Engine separation, no trade execution, TL/HL/CH/direction-arrow drawing scope, and ChatGPT judgment ownership. Other non-conflicting technical clauses below remain in force until separately reviewed.

This document fixes the contract for the NODA Chart Annotator Live Draw path. It does **not** change NODA Engine rules R01–R20. Detector details explicitly marked PROVISIONAL may be tuned in TEST without changing this fixed contract.

## 1. Purpose

NODA Chart Annotator (NCA) now has two distinct roles:

1. **Live Draw** — use MT4 OHLC to recognize structure and draw TL / CH / Zone.
2. **Teacher Benchmark** — preserve Teacher PDF / Chatwork `分析共有` acquisition and prior PDF/geometry regression assets for later comparison and refinement.

Teacher PDF agreement is **not** a Live Draw pass gate.

## 2. Environments

Operational names are fixed as:

- `TEST` — detector, line-selection, lifecycle, and renderer verification.
- `LIVE` — continuous drawing using logic already verified in TEST.

Legacy internal IDs may remain only for compatibility:

- `TEST1` -> `TEST`
- `PROD2` -> `LIVE`

## 3. Initial instruments

Canonical symbols:

- `USDJPY`
- `GOLD`
- `US100`

Broker symbols are resolved only by the symbol adapter. Initial XM mappings are:

- `USDJPY` -> `USDJPY#`
- `GOLD` -> `GOLD#`
- `US100` -> `US100Cash#`

Canonical and broker symbols must never be treated as the same field.

## 4. Timeframes

Live Draw v1 observes:

- `D1`
- `H4`
- `H1`
- `M15`

Timeframe and structural level are independent. Fixed mappings such as `D1 = LARGE_DOW` or `H4 = MID_DOW` are prohibited.

## 5. Structural levels

Live Draw v1 outputs only:

- `LARGE_DOW`
- `MID_DOW`

Small-Dow structure may be used internally for Turn detection but is not a primary Live Draw output level.

## 6. Draw object hierarchy

Primary object:

- `TL`

Dependent objects:

- `CH`
- `TL_ZONE`
- `CH_ZONE`

`CH` and both Zones are subordinate to a selected TL. CH must not create an independent primary structure.

Initial non-goals / HOLD:

- HL / horizontal Zone
- FIB
- Scenario
- Entry / SL / TP / RR / Lot
- Long / Short / Order / Ticket
- trading decisions or order actions

NCA must not write new rules or detector semantics back into NODA Engine.

## 7. Live Draw flow

```text
High / Low facts
    -> Turn
    -> Large-Dow / Mid-Dow structure
    -> TL selection inside TL-generation
    -> TL fixed
    -> CH generated
    -> TL Zone / CH Zone generated
```

TL selection evaluates anchor relation, TL-side reaction, CH-side reaction, and the coherence of the TL+CH channel as one structure. Internal temporary alternatives are allowed, but only the selected TL is published to Snapshot / MT4.

## 8. Line lifecycle contract

A line break is not, by itself, a redraw or delete trigger.

```text
TL Break != New TL
TL Break != Delete old TL
```

New TL generation waits for price progression followed by a completed N / Turn and a newly confirmed high or low. The structural level is then re-evaluated, anchors are re-selected, and the new TL is created.

Old TL deletion is a separate operation. An old TL is removable only after:

1. a new Turn / new high or low is confirmed,
2. a new TL is established, and
3. the old TL no longer has an active structural role.

If either Large-Dow or Mid-Dow still references the old TL, it must not be immediately removed.

## 9. Generation retention

For each managed structural line family, keep at most two displayed generations:

- current TL,
- immediately previous TL.

When a third generation is established, the oldest generation is removed from the MT4 display. CH and Zones inherit the generation lifecycle of their parent TL.

Deletion from the display must not mean deletion from history. The architecture must remain compatible with a future lifecycle log containing symbol, timeframe, structure level, old/new IDs, reason, anchors, and timestamp.

## 10. Zone contract

TL Zone uses the start-anchor candle wick-to-body range as the base width. Fixed pip width and ATR width are prohibited.

CH Zone uses the **same width as TL Zone**, translated in price to the CH side. CH-side width is not independently recalculated in v1.

Advanced outlier-wick exclusion or body-extension logic is not required for v1.

## 11. Confirmed-bar policy and schedule

Unconfirmed bars must not change structure.

All Turn / structure / TL / CH updates use closed bars only. The initial Live Pipeline cadence is after M15 close, approximately:

- `00:01`
- `15:01`
- `30:01`
- `45:01`

D1 / H4 / H1 are checked within the same cycle and are updated only when their relevant closed-bar inputs changed.

## 12. Market and Teacher pipelines

### Market Pipeline — required for Live Draw

```text
MT4 OHLC
 -> USDJPY / GOLD / US100
 -> D1 / H4 / H1 / M15
 -> Turn
 -> Large-Dow / Mid-Dow
 -> TL / CH / Zone
 -> MT4 Draw
```

### Teacher Pipeline — benchmark only

Existing Chatwork `分析共有` collection continues. Existing PDF extraction, geometry consolidation, Teacher regression, repeated selection, candidate/formal parity, and Formal Test Overlay assets are retained as Teacher Benchmark / Regression evidence.

A missing Teacher PDF must never stop Live Draw.

## 13. Fixed vs provisional

### FIXED CONTRACT

- TEST / LIVE responsibilities
- 3 initial canonical symbols
- 4 timeframes
- Large-Dow / Mid-Dow output levels
- TL primary; CH / Zones subordinate
- lifecycle: Break does not immediately redraw/delete
- current + previous generation only
- closed bars only
- Market Pipeline independent from Teacher Benchmark
- NODA Engine separation
- hard trade-field prohibition

### PROVISIONAL DETECTORS

- 38% close-based Turn Detector v1
- exact Large-Dow / Mid-Dow machine-classification details
- exact CH-break confirmation details

PROVISIONAL detectors may be tuned locally in TEST. Changes to the FIXED CONTRACT require a separate work item and explicit approval.

## 14. Hard prohibitions

Do not introduce:

- fixed pip thresholds,
- ATR thresholds,
- ML scores,
- strength scores,
- RSI / MACD / Bollinger Bands,
- Entry / SL / TP / RR / Lot,
- Long / Short / trade direction,
- Order / Ticket,
- trading decisions,
- fixed timeframe-to-Dow mapping.

## 15. Baseline declaration

```text
NCA LIVE DRAW BASELINE V1
STATUS: FIXED / SUBORDINATE TO BOUNDARY V1
```
