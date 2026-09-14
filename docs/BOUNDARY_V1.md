# NODA Chart Annotator — Boundary v1

Status: **FIXED**  
Fixed date: **2026-09-14**  
Revision note: runtime judgment ownership corrected on **2026-09-14** to match the working implementation.

This document is the top-level boundary contract for the MT4① drawing system.
When another NCA document conflicts with this Boundary v1, **Boundary v1 takes precedence**.

## Fixed boundary

| Item | Fixed definition | Status |
|---|---|---|
| Purpose | Draw lines and arrows on the **MT4① chart** | FIXED |
| Target MT4 | **MT4① only** | FIXED |
| Symbol names | Use **XM MT4 symbol names as the canonical names** | FIXED |
| TC | **Do not use, do not depend on, and no future integration is planned** | FIXED |
| TC consumption | **Out of scope** | FIXED |
| Market hours | **Do not use market-hours logic as a judgment or execution condition** | FIXED |
| NODA Engine | **Separate system. Do not integrate the drawing system into NODA Engine** | FIXED |
| Trade execution | **None. No authority to place/close/modify orders or modify SL/TP** | FIXED |
| Drawing targets | **TL / HL / CH / direction arrow** | FIXED for Boundary v1 |
| Judgment owner | **NCA local drawing logic judges what to draw; MT4① renders the resulting drawing state. ChatGPT is not part of the runtime judgment path.** | FIXED |

## Consequences

1. XM MT4 symbols are the system identity. Internal aliases must not replace the XM symbol name as the canonical identifier.
2. TradingCursor/TC, TC cache/refresh policy, TC provider symbols, TC call count, and TC operating windows are not design inputs for this system.
3. Market-open/closed calendars and session-time gating are not used to decide whether drawing judgment may run.
4. NODA Engine remains independent and must not receive drawing-system logic, state, or implementation changes.
5. The system is drawing-only. It must not gain order-send, close, modify, SL/TP-change, sizing, lot, or ticket authority.
6. MT4① is the only drawing destination in Boundary v1.
7. The runtime drawing judgment stays inside NCA local logic (currently Python). MT4① is the rendering destination. ChatGPT is not a runtime dependency and is not inserted between market data and drawing output.
8. ChatGPT may be used outside the runtime for specification review, audit, or development discussion, but that must not change the live drawing dependency chain.

## Precedence

This file supersedes conflicting statements in older NCA documents, including but not limited to:

- canonical symbol naming that uses non-XM aliases,
- drawing-target restrictions that exclude HL or direction arrows,
- assumptions that another engine or TC is part of the active drawing path,
- schedule or market-hours rules presented as a Boundary-level execution condition,
- any wording that makes ChatGPT part of the runtime drawing judgment path.

Items not addressed by Boundary v1 remain governed by their existing document until separately reviewed and fixed.

```text
NCA BOUNDARY V1
STATUS: FIXED
TARGET: MT4①
CANONICAL SYMBOLS: XM MT4 SYMBOL NAMES
DRAW: TL / HL / CH / DIRECTION ARROW
JUDGMENT: NCA LOCAL LOGIC (CURRENTLY PYTHON)
CHATGPT: NOT IN RUNTIME DRAWING PATH
TC: PROHIBITED / NO DEPENDENCY / NO FUTURE PLAN
NODA ENGINE: SEPARATE
TRADE EXECUTION: NONE
```
