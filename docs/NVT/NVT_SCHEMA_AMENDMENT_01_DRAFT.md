# NVT Ground Truth Schema Amendment 01 — DRAFT

Status: **DRAFT / NOT FIXED**  
Date: 2026-09-15

This document records schema gaps discovered only after reviewing the initial USDJPY teacher-video corpus. It does not modify `GROUND_TRUTH_SCHEMA_V1.md` yet.

## 1. Gap A — explicit NO-LINE result

Repeated teacher evidence shows that the correct result may be **no TL/CH for the structure currently being evaluated**.

Examples:

- 2026-08-08 H1: teacher explicitly says the H1 chart does not need a line; if desired, the line belongs to M15 internal structure.
- 2026-09-12 H1: teacher declines one apparent H1 turn line because the shown shape represents the wrong structural scale.
- 2026-09-05 H1: teacher says the H1 line is difficult/not yet drawable.

Proposed v1.1 field:

```text
expected_draw_state: DRAW | NO_LINE | CONDITIONAL | UNKNOWN
```

This should be separate from event `action` because `NO_LINE` is a target state, not necessarily a transition performed on an existing object.

### NO-LINE scope is also required

Further review of GT_0005 and GT_0006 shows that NO-LINE cannot always be interpreted as a global ban on every line on the same chart/timeframe. GT_0005 rejects the **shown apparent structure**, while GT_0006 shortly afterward discusses a different H1 descending TL structure on the same market data.

Therefore a second field is required in addition to `expected_draw_state`:

```text
no_line_scope: TIMEFRAME_GLOBAL | STRUCTURE_SPECIFIC | OBJECT_SPECIFIC | UNKNOWN
```

Interpretation:

```text
TIMEFRAME_GLOBAL
  no teacher TL/CH should be produced for the timeframe/task state shown.

STRUCTURE_SPECIFIC
  the particular structural interpretation being evaluated should produce no line,
  but another independently valid structure on the same timeframe may still exist.

OBJECT_SPECIFIC
  one proposed/legacy object should be absent while other objects may remain.
```

Provisional evidence:

```text
GT_0007 -> TIMEFRAME_GLOBAL candidate
GT_0005 -> STRUCTURE_SPECIFIC candidate
GT_0006 -> DRAW case on the same H1 source/cutoff as GT_0005
```

This distinction is important for Structure Ownership research. A selector/ownership gate must not learn `GT_0005 = no H1 lines anywhere`; it must learn why the rejected structure belongs to a different scale.

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

## 5. Gap E — candidate/task target identity for NO-LINE evidence

A structure-specific NO-LINE record needs a way to state **what was rejected** even when no teacher object is created.

Proposed optional fields:

```text
rejected_structure_hint:
  direction
  approximate_anchor_window
  structure_scale_hint
  lower_timeframe_alternative
```

These fields must distinguish source-derived evidence from analyst inference. Exact anchors remain UNKNOWN unless verified from frame/OHLC evidence.

Without this target identity, case-level candidate counts cannot be used as a clean negative label because unrelated valid candidates may coexist.

## 6. Fixed-schema discipline

Do not change `GROUND_TRUTH_SCHEMA_V1.md` until NVT1/NVT5 review confirms these needs across sufficient cases.

Current DRAFT cases encode NO-LINE as empty `teacher_objects` plus notes so no silent incompatible schema change is introduced.

## 7. Proposed decision gate

Amendment 01 may become v1.1 only after:

```text
>= 2 independent NO-LINE examples       already observed
>= 2 timeframe-ownership examples       already observed
>= 1 structure-specific NO-LINE case    observed (GT_0005)
>= 1 timeframe-global NO-LINE case       observed (GT_0007)
>= 1 role-reclassification example      observed conceptually; needs explicit event confirmation
```

Status now:

```text
NO_LINE need: CONFIRMED
NO_LINE scope need: CONFIRMED
TF ownership need: CONFIRMED
Rejected-structure target need: CONFIRMED
RECLASSIFY need: PROBABLE
VALID-ALTERNATIVE vs PREFERRED: CONFIRMED
AMENDMENT FIXED: NO
```
