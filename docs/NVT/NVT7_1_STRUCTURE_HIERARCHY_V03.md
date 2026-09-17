# NVT7.1 Structure Hierarchy / Line Role V0.3

Status: RESEARCH ONLY / USER OPERATIONAL EVIDENCE / USDJPY H1

## Purpose

V0.3 finalizes two previously unresolved break semantics and fixes the current automatic display policy for `TURN_LINE`.

This revision keeps the V0.2 separation between:

1. line role,
2. visibility,
3. Dow hierarchy state,
4. structural-high confirmation.

It still does **not** modify frozen NVT7, Production Normal Run, Production `tools/live_draw`, MT4 objects, or trading authority.

## 1. Line roles

### `LARGE_DOW_TL`

User example: pink TL.

- Primary large-Dow structural trendline.
- Default visibility: `DRAW`.
- Its importance is not created by a small-Dow high breakout.

### `TURN_LINE`

User example: red TL.

- Local/internal turn line.
- May be used for structure interpretation.
- Default visibility: `VALID_SUPPRESSED`.
- Current automatic display exceptions: **none**.
- A local high breakout does not promote it into a major line and does not make it automatically visible.
- Any future automatic-display exception requires new evidence and a new version.

## 2. Closed-bar structural break rule

The user fixed both pending break questions to **closed-bar close**.

### High / gate break

For an upward break:

```text
close > ACTIVE_HIGH_OR_GATE
    -> BREAK_CONFIRMED
```

A wick-only penetration does not count.

This applies to the small-Dow high break used to establish `SMALL_DOW_RISING` and to the active large-Dow high gate used for `LARGE_DOW_PROMOTED`.

### Protected-low break

For `LAST_PULLBACK_LOW` / `PROTECTED_LOW`:

```text
close < LAST_PULLBACK_LOW
    -> PROTECTED_LOW_BROKEN
```

A wick-only penetration does not count.

## 3. Dow hierarchy

```text
small-Dow high broken by CLOSED_BAR_CLOSE
    -> SMALL_DOW_RISING
    -> LARGE_DOW_NOT_PROMOTED
    -> ACTIVE_LARGE_DOW_HIGH remains next major resistance

ACTIVE_LARGE_DOW_HIGH broken by CLOSED_BAR_CLOSE
    -> LARGE_DOW_PROMOTED
```

A lower-order breakout is therefore not a substitute for parent-structure promotion.

## 4. Structural high confirmation

Preferred term: `STRUCTURAL_HIGH`.
Alternate term: `SWING_HIGH`.

A rising-wave apex begins as `SWING_HIGH_CANDIDATE`.

Two evidence signals remain stored independently:

### `RETRACE_38_CONFIRMED`

- Existing 38% detector evidence is reused.
- Existing Production detector behavior is not changed.
- Confirmation basis remains later closed-bar close across the 38% threshold.

### `PROTECTED_LOW_BROKEN`

- Protected low = `LAST_PULLBACK_LOW`.
- Confirmed only by a later closed-bar close below that low.
- Wick-only penetration does not count.

Research state:

```text
38% false + protected low false
    -> SWING_HIGH_CANDIDATE

exactly one true
    -> STRUCTURAL_HIGH_PARTIAL

38% true + protected low true
    -> STRUCTURAL_HIGH_CONFIRMED_STRONG
```

## 5. Resistance context

If:

```text
SMALL_DOW_RISING = true
LARGE_DOW_PROMOTED = false
```

then:

```text
NEXT_MAJOR_RESISTANCE = ACTIVE_LARGE_DOW_HIGH
```

This is structural context only, not an automatic take-profit or order instruction.

## 6. What remains unresolved

Only this item remains deliberately unfixed in this scoped semantic contract:

- objective deterministic classification of pivots into `SMALL_DOW` / `MID_DOW` / `LARGE_DOW` in every case.

This is the next research problem; it is not silently inferred from the mechanical Large/Mid labels.

## 7. Supersession

V0.3 supersedes V0.2 only where V0.2 explicitly left items open:

- high/gate break is now `CLOSED_BAR_CLOSE`,
- protected-low break is now `CLOSED_BAR_CLOSE`,
- automatic `TURN_LINE` display exception is currently none.

The prior B02_03 and V0.2 artifacts remain retained for audit history.

## 8. Promotion policy

V0.3 may be used as the current **research-scoped semantic freeze contract** after its contract runner passes.

It is not:

- Teacher Ground Truth,
- strict NVT8 held-out validation,
- NVT9 Production promotion,
- permission to modify `NCA_DRAW__`,
- permission to modify Production `tools/live_draw`,
- trade/order authority.
