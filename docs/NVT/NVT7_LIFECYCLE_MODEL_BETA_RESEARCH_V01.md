# NVT7 Lifecycle Model Beta Research v0.1

Status: **RESEARCH ONLY / NOT PRODUCTION FIXED**

## Purpose

NVT7 models how a teacher-like drawing changes after a candidate has already been judged structurally valid. It is deliberately separated from NVT6 candidate recall/ownership/selection.

Production `tools/live_draw/`, production selector/lifecycle behavior, Normal Run, `NCA_DRAW__`, MT4 objects, and trade authority remain untouched until NVT9.

## Evidence cases

### GT_0002 — update current while retaining useful reference

- The updated channel may become the current channel.
- The initial channel may remain because it still serves a reference/target role.
- Therefore, `new current` does **not** imply `delete old`.

### GT_0004 — persistent monitoring reference can beat a newer re-anchor

- A long-retained original line can be more useful for monitoring continuity than a newer re-anchored candidate.
- Chronological recency and geometric validity are insufficient by themselves to define lifecycle preference.

### GT_0005 — valid but intentionally hidden

- Small-Dow turn line is structurally valid.
- It may be steep and short-lived.
- The teacher may suppress its display to avoid line clutter.
- Therefore validity and visibility are separate lifecycle dimensions.

### GT_0006 — selector/lifecycle boundary

- Same MT4 object name is observed across multiple geometry states.
- No one fixed Gate-C geometry explains all direct video samples.
- Some samples match stable candidate geometries; one sample has no tight fixed-candidate match and must remain transient/unresolved.
- Video edit order must not be equated with market-time lifecycle order.

## Provisional state hypotheses

These names are research labels only and are not fixed production semantics.

```text
CURRENT_ACTIVE
REFERENCE_RETAINED
VALID_SUPPRESSED
EDIT_TRANSIENT
REANCHORED_CURRENT
```

`RETIRED` / `DELETE` is intentionally **not** fixed yet. NVT7 needs explicit evidence before using deletion as a default state transition.

## Provisional transition hypotheses

```text
CURRENT_ACTIVE
  -> REANCHORED_CURRENT + REFERENCE_RETAINED
     when a newer active geometry is useful but the old structure still has reference value

VALID_CANDIDATE
  -> VALID_SUPPRESSED
     when the line is valid but short-lived / steep / display-clutter cost is high

NEWER_REANCHOR_OR_PC_EDIT
  -> REFERENCE_RETAINED
     when persistent monitoring continuity is more useful than the newer re-anchor
```

No hypothesis above is a hard rule yet.

## NVT7-1 processing order

1. Parse GT_0002 / GT_0004 / GT_0005 semantic lifecycle evidence.
2. Load the NVT6 GT_0006 visual state-sequence result.
3. Separate stable geometry candidates from transient/unresolved edit samples.
4. Build a case-by-state and case-by-transition evidence matrix.
5. Verify guards before any lifecycle beta rule is frozen.

## Hard research guards

- latest is not automatically best;
- newest current does not automatically delete an old useful reference;
- valid does not imply visible;
- hidden does not imply invalid;
- same MT4 object name does not imply same geometry;
- video drag/edit order does not automatically equal market-time transition order;
- transient edit samples must not become stable lifecycle states;
- deletion/retirement requires explicit evidence.

## NVT7-1 gate

NVT7 research may continue only if all of the following are evidenced:

```text
GT_0002: CURRENT + REFERENCE coexistence evidence
GT_0004: persistent-reference preference evidence
GT_0005: valid-but-suppressed evidence
GT_0006: multiple geometry states + no single fixed geometry across all samples
GT_0006: transient/unresolved sample separated from stable candidates
```

Passing this gate only means the lifecycle evidence basis is internally consistent. It does **not** make any production lifecycle rule ready.

## Next after preflight

NVT7-2 will construct an explicit research event/state graph and sequential regression covering:

```text
KEEP
UPDATE / REANCHOR
KEEP-REFERENCE
SUPPRESS
RESTORE-REFERENCE
TRANSIENT-EDIT
```

Exact deletion/retirement semantics remain pending evidence.
