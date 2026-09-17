# NVT7.1 Structure Hierarchy / Line Role V0.2

Status: RESEARCH ONLY / USER OPERATIONAL EVIDENCE / USDJPY H1

## Purpose

This revision supersedes the earlier B02_03 simplification that treated a local structural-high breakout as a line-promotion event.

The user evidence now separates four different concepts:

1. **line role** — what the line is (`LARGE_DOW_TL` vs `TURN_LINE`),
2. **visibility** — whether it should normally be drawn,
3. **Dow hierarchy state** — small-Dow rising vs large-Dow promotion,
4. **structural-high confirmation** — whether a wave high is only a candidate, partially confirmed, or strongly confirmed.

This document does **not** modify frozen NVT7, Production Normal Run, Production `tools/live_draw`, MT4 objects, or trading authority.

## 1. Line roles

### `LARGE_DOW_TL`

User example: pink TL.

- Primary structural trendline.
- Default visibility: `DRAW`.
- Its importance is not created by a small-Dow high breakout.
- It remains a higher-order structural reference even while local/internal movement occurs.

### `TURN_LINE`

User example: red TL.

- Local/internal turn line.
- Technically valid for structure interpretation.
- Default visibility: `VALID_SUPPRESSED`.
- It is normally **not drawn**.
- A local high breakout does **not** promote it into a major line.
- Any future automatic-display exception must be separately evidenced and specified.

Therefore:

```text
TURN_LINE + local breakout
    -> TURN_LINE
    -> VALID_SUPPRESSED
```

not:

```text
TURN_LINE + local breakout
    -> IMPORTANT / MAJOR TL
```

## 2. Dow hierarchy

A break of a lower-order high and a promotion of the parent structure are different events.

```text
small-Dow high broken
    -> SMALL_DOW_RISING
    -> LARGE_DOW_NOT_PROMOTED
    -> ACTIVE_LARGE_DOW_HIGH remains the next major resistance/gate

ACTIVE_LARGE_DOW_HIGH broken
    -> LARGE_DOW_PROMOTED
```

This corrects the earlier shortcut in which a lower-order breakout was allowed to stand in for parent-structure promotion.

The active large-Dow high may be the first meaningful high, an updated high, or the current relevant large-Dow swing/structural high. The exact deterministic scale classifier is not frozen yet.

## 3. Structural high / swing high

Preferred implementation term:

`STRUCTURAL_HIGH`

Alternate descriptive term:

`SWING_HIGH`

A rising-wave apex starts as:

`SWING_HIGH_CANDIDATE`

Two confirmation signals are tracked **independently**.

### A. `RETRACE_38_CONFIRMED`

- The rise has retraced at least 38%.
- Existing Production turn-detector evidence may be reused.
- Production detector behavior is not changed.
- The current detector confirms using a later **closed-bar close** crossing the 38% threshold.

### B. `PROTECTED_LOW_BROKEN`

- `PROTECTED_LOW` is the last pullback low protecting the rise.
- Alternate implementation name: `LAST_PULLBACK_LOW`.
- When that low is broken, the prior high gains additional structural confirmation.
- Whether the break requires wick penetration or closed-bar close remains unfixed.

Research state:

```text
38% false + protected low false
    -> SWING_HIGH_CANDIDATE

exactly one true
    -> STRUCTURAL_HIGH_PARTIAL

38% true + protected low true
    -> STRUCTURAL_HIGH_CONFIRMED_STRONG
```

The two booleans must remain separate in research output so later evidence can change how they are combined without rewriting the raw observations.

## 4. Resistance context

If:

```text
SMALL_DOW_RISING = true
LARGE_DOW_PROMOTED = false
```

then:

```text
NEXT_MAJOR_RESISTANCE = ACTIVE_LARGE_DOW_HIGH
```

This is structural context only. It is not an automatic order or take-profit instruction.

## 5. Superseded B02_03 interpretations

The historical B02_03 evidence artifact remains retained for audit, but these interpretations are superseded:

### Superseded

`red-circle / local structural-high breakout -> local TL becomes important line`

### Replacement

`local structural-high breakout -> local Dow state changes; TURN_LINE remains TURN_LINE and normally VALID_SUPPRESSED`

---

### Superseded

`second post-break low universally confirms/promotes the large-Dow TL`

### Replacement

`large-Dow TL identity/importance is a separate higher-order structural role; do not use the second-low event as a universal line-promotion shortcut`

## 6. Still unfixed

The following are deliberately **not** invented in V0.2:

- high/gate break = wick or closed-bar close,
- protected-low break = wick or closed-bar close,
- universal automatic classification from pivots into `SMALL_DOW` / `MID_DOW` / `LARGE_DOW`,
- automatic exceptions that make `TURN_LINE` visible.

These do not block a research semantic freeze candidate because the model stores the unresolved observations separately.

## 7. Promotion policy

V0.2 may be frozen as a **research-scoped semantic contract** after regression checks pass.

It is **not**:

- Teacher Ground Truth,
- strict NVT8 held-out validation,
- NVT9 Production promotion,
- permission to modify `NCA_DRAW__`,
- permission to modify Production `tools/live_draw`,
- trade/order authority.
