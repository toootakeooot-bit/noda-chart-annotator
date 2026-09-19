# NVT9 Display Review Plan V0.1

Status: REVIEW ONLY / NO RENDERER CHANGE  
Date: 2026-09-19  
Audit ID: ID10IQ200

## Current display formula

When LARGE_DOW and MID_DOW both have CURRENT and PREVIOUS generations, Snapshot publishes:

- 2 structure levels;
- 2 generations;
- 4 roles per generation: TL, CH, TL_ZONE_EDGE, CH_ZONE_EDGE.

Therefore:

```
2 x 2 x 4 = 16 MT4 objects per timeframe
```

This is why D1/H4/H1/M15 all reported 16 objects in the USDJPY# smoke run.

## Why H1 looks especially crowded

The object count itself is not higher on H1. The visible density is higher because several selected structures are close in price and slope, so:

- LARGE_DOW and MID_DOW can visually overlap;
- CURRENT and PREVIOUS can remain close to each other;
- TL and TL_ZONE_EDGE form a close pair;
- CH and CH_ZONE_EDGE form another close pair.

Therefore H1 crowding can be a display-policy issue even when structure selection is internally consistent.

## Review order

Do not change detector/selector first.

Review in this order:

1. PREVIOUS role visibility;
2. zone-edge visibility;
3. MID_DOW visibility;
4. only then reconsider structure selection if the remaining primary TL/CH is still wrong.

This prevents a display problem from being mistaken for a structure-selection problem.

## Candidate display profiles for TEST

These are review candidates only. They are not Production settings.

| Profile | CURRENT LARGE | CURRENT MID | PREVIOUS LARGE | PREVIOUS MID | Approx. rows |
|---|---|---|---|---|---:|
| BASELINE_FULL | TL/CH/2 zone edges | TL/CH/2 zone edges | TL/CH/2 zone edges | TL/CH/2 zone edges | 16 |
| REVIEW_A | TL/CH/2 zone edges | TL/CH/2 zone edges | TL/CH | TL/CH | 12 |
| REVIEW_B | TL/CH/2 zone edges | TL/CH/2 zone edges | TL | TL | 10 |
| REVIEW_C | TL/CH/2 zone edges | TL/CH | TL/CH | TL | 9 |

Interpretation:

- REVIEW_A removes only PREVIOUS zone edges. This is the smallest visibility reduction.
- REVIEW_B keeps previous structural TL references but removes previous CH and zones.
- REVIEW_C also removes CURRENT MID zone edges and keeps only a minimal PREVIOUS MID reference.

No profile is selected yet.

## Evidence required before choosing a profile

For every displayed line set, review:

- timeframe;
- LARGE_DOW or MID_DOW;
- CURRENT or PREVIOUS;
- direction;
- anchor1 and anchor2 time/price;
- Turn confirmation time;
- candidate pool size;
- turn_span;
- TL contact count;
- CH contact count;
- unbroken-close state;
- CH anchor and offset;
- zone width;
- reason it remains visible.

The NVT9 draw-rationale report provides these fields without changing drawing behavior.

## Decision rule

If the primary TL/CH anchors are correct but the chart is crowded, change display policy only.

If the primary TL/CH anchors themselves are wrong, reopen the appropriate semantic layer instead of hiding the error with renderer settings.

## Production protection

This review does not change:

- Turn detector;
- candidate generation;
- selector;
- lifecycle;
- Snapshot semantics;
- Production Renderer;
- NCA_DRAW__ ownership or objects.
