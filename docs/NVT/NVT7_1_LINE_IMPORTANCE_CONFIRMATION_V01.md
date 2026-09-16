# NVT7.1 Line Importance / Confirmation Candidate V0.1

Status: RESEARCH ONLY / USER OPERATIONAL EVIDENCE / USDJPY H1

## Purpose

B02_03 shows that four concepts must not be collapsed into one boolean `draw_line` decision:

1. whether a line can be drawn,
2. whether H1 direction has structurally resumed,
3. whether the line is important enough to become a current monitoring line,
4. whether the line has enough post-break low confirmation to be treated as a large-Dow TL.

This document does **not** modify the frozen NVT7 scoped beta or Production Normal Run.

## Evidence case

- Case: `USDJPY_NVT71_B02_03`
- Cutoff: `2026-06-22 23:00` broker time
- Evidence class: `USER_OPERATIONAL_EVIDENCE`
- Teacher validation: no

User adjudication:

- While price remains within the small-Dow / mid-Dow horizontal-level structure, H1 is treated as range and **not yet rising**.
- A cyan rising TL may be drawable during that range, but it is provisional.
- Only after price exceeds the user-marked structural high (red-circle point) is H1 considered to have resumed rising direction.
- That breakout promotes the previously drawable line into an **important** line candidate.
- After the breakout, lows are searched again. When a second valid low reacts at the mid-Dow upper horizontal level, the large-Dow TL becomes confirmable as a current line.

## Required model separation

### A. Direction state

`RANGE_NOT_H1_RISING -> RISING_RESUMED`

Promotion trigger:

`BREAK_ABOVE_STRUCTURAL_HIGH`

Important guard:

Mechanical `baseline_large.direction == RISING` and `baseline_mid.direction == RISING` are insufficient, by themselves, to set the user-semantic H1 state to rising.

### B. Drawability state

`NOT_DRAWN | PROVISIONAL_DRAWABLE | DRAWN`

A line may enter `PROVISIONAL_DRAWABLE` before the H1 direction-resume trigger.

### C. Importance / confirmation phase

Research candidate phases:

1. `PROVISIONAL_DRAWABLE`
   - geometry can be drawn,
   - not yet important,
   - not decision owner.

2. `IMPORTANT_CANDIDATE`
   - structural-high breakout has occurred,
   - H1 rising has resumed,
   - line now matters for monitoring,
   - still may await full large-Dow confirmation.

3. `CURRENT_CONFIRMED_LARGE_DOW_TL`
   - post-break low search has produced the second valid low,
   - the second low reacts at the relevant mid-Dow horizontal level,
   - the line may be treated as the confirmed large-Dow current TL.

### D. Visibility

Visibility remains a separate dimension from importance and confirmation. Existing NVT7 semantics such as `REFERENCE_RETAINED` and `VALID_SUPPRESSED` are not overwritten here.

### E. Decision ownership

Decision ownership also remains separate. A provisional or visible line is not automatically the primary decision owner.

## State transition candidate

```text
RANGE_NOT_H1_RISING
    |
    | geometry exists
    v
PROVISIONAL_DRAWABLE
    |
    | red-circle / structural-high breakout
    v
RISING_RESUMED + IMPORTANT_CANDIDATE
    |
    | second post-break valid low
    | reacting at mid-Dow upper HL
    v
CURRENT_CONFIRMED_LARGE_DOW_TL
```

## What this corrects

Earlier B02_03 simplification treated mechanical H1 Large/Mid `RISING` as if the user-semantic parent direction were already rising. The user adjudication corrects that interpretation:

- local `FALLING` does not automatically mean H1 downtrend,
- mechanical Large/Mid `RISING` does not automatically mean H1 has resumed uptrend,
- unresolved range is a legitimate intermediate structural state.

Therefore the direction domain must support an intermediate `RANGE_NOT_H1_RISING` state rather than forcing binary `RISING/FALLING` semantics.

## Non-goals / unfixed items

- No numeric breakout buffer is fixed.
- No exact red-circle price is locked from this evidence alone.
- No universal definition of small-Dow or mid-Dow horizontal-level extraction is fixed here.
- No automatic second-low tolerance is fixed.
- No Production renderer behavior changes.
- No order/trade authority.

## Promotion policy

This evidence may be used to build and regression-test an NVT7.1 research candidate. It must not amend the frozen NVT7 beta or Production semantics until additional historical cases and/or teacher evidence support the same transition pattern.
