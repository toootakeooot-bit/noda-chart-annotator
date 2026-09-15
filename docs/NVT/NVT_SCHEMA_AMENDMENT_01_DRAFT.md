# NVT Ground Truth Schema Amendment 01 — DRAFT

Status: **DRAFT / NOT FIXED**  
Date: 2026-09-15

This document records schema gaps discovered only after reviewing the initial USDJPY teacher-video corpus. It does not modify `GROUND_TRUTH_SCHEMA_V1.md` yet.

## 1. Gap A — explicit NO-LINE result

Repeated teacher evidence shows that the correct result for a timeframe can be **no TL/CH at all**.

Examples:

- 2026-08-08 H1: teacher explicitly says an H1 line is unnecessary; if desired, the line belongs to M15 internal structure.
- 2026-09-12 H1: teacher declines to draw the apparent turn line because it represents the wrong structural scale.
- 2026-09-05 H1: teacher says the H1 line is difficult/not yet drawable.

Proposed v1.1 field:

```text
expected_draw_state: DRAW | NO_LINE | CONDITIONAL | UNKNOWN
```

This should be separate from event `action` because `NO_LINE` is a target state, not necessarily a transition performed on an existing object.

## 2. Gap B — structure ownership timeframe vs display timeframe

Teacher evidence distinguishes:

- the timeframe/market wave that **owns** a structure;
- the chart timeframe currently used to inspect or display it.

Proposed per-object fields:

```text
structure_owner_timeframe
display_timeframe
```

This allows cases such as:

```text
H1 chart visible
but candidate represents M15 internal wave
```

without falsely labeling it as an H1 structural line.

## 3. Gap C — explicit reclassification

Some lines can change role without being geometrically replaced, e.g. active line -> retained reference.

Proposed event action addition:

```text
RECLASSIFY
```

with optional fields:

```text
role_before
role_after
```

## 4. Gap D — valid alternative vs preferred teacher line

Video evidence shows multiple candidates can be structurally valid while the teacher prefers one for usability/monitoring.

Proposed comparison fields:

```text
teacher_valid_alternative: true | false | unknown
teacher_preferred: true | false | unknown
```

This prevents treating every non-preferred but valid line as an outright geometric error.

## 5. Fixed-schema discipline

Do not change `GROUND_TRUTH_SCHEMA_V1.md` until NVT1 video review confirms these needs across sufficient cases.

Current DRAFT cases encode NO-LINE as empty `teacher_objects` plus notes so no silent incompatible schema change is introduced.

## 6. Proposed decision gate

Amendment 01 may become v1.1 only after:

```text
>= 2 independent NO-LINE examples       already observed
>= 2 timeframe-ownership examples       already observed
>= 1 role-reclassification example      observed conceptually; needs explicit event confirmation
```

Status now:

```text
NO_LINE need: CONFIRMED
TF ownership need: CONFIRMED
RECLASSIFY need: PROBABLE
VALID-ALTERNATIVE vs PREFERRED: CONFIRMED
AMENDMENT FIXED: NO
```
