# NCA Live Draw Lifecycle v1

Status: **FIXED CONTRACT**  
Normal Run precedence note: **updated 2026-09-14**

This document fixes how TL-centered draw objects are added, retained, replaced, and removed.
`docs/BOUNDARY_V1.md` is the top-level contract and `docs/DRAWING_OPERATION_V1.md` is the active operating contract. Where prior state-retention wording in this Lifecycle document conflicts with Normal Run history rebuild, **Drawing Operation v1 takes precedence**.

CH and Zones inherit their lifecycle from the parent TL unless explicitly noted.

## 1. Primary lifecycle object

TL is the primary lifecycle object.

A managed family is:

```text
TL_xxx
├─ CH_xxx
├─ TL_ZONE_xxx
└─ CH_ZONE_xxx
```

CH may move while the parent TL remains fixed, but CH never becomes the owner of the family.

## 2. States

Minimum required TL states:

- `ACTIVE` — current structural TL.
- `BROKEN_WAIT_TURN` — price has broken the TL, but a new Turn / new high or low has not yet confirmed the replacement structure.
- `PREVIOUS` — immediate prior TL retained for one generation.
- `RETIRED` — no longer displayed, but retained in history/audit data.

State names may be implemented differently internally, but these semantics must be preserved.

For **Normal Run**, `ACTIVE` and `PREVIOUS` must be derived from the present chronological rebuild of closed-bar history. A persisted slot from a prior run may be used as implementation data or audit evidence, but it is **not authoritative** merely because it was saved previously.

## 3. Break is observational, not replacement

A break event alone does not redraw or delete.

```text
ACTIVE
  -> break observed
BROKEN_WAIT_TURN
```

During chronological reconstruction, a break remains observational until a new Turn / new high or low confirms the replacement structure. A line must not become a new generation solely because price crossed the prior line.

## 4. New TL creation

A new TL generation may be created only after the structural sequence below:

```text
existing TL
 -> break or continued price progression
 -> N / Turn formation
 -> new high or low confirmed
 -> Large-Dow / Mid-Dow re-evaluation
 -> new valid anchors
 -> TL-selection process
 -> new TL
```

The key gate is **new structural confirmation**, not the line break itself.

During Normal Run, this sequence is evaluated chronologically across the acquired closed-bar history so intervening TL generations can be reconstructed even when NCA was not run at the time they originally occurred.

## 5. TL selection occurs inside generation

Do not expose a pool of unresolved TL candidates as normal output.

The generator may temporarily evaluate multiple anchor combinations internally. Selection must consider:

- anchor relation,
- TL-side reaction,
- CH-side reaction,
- overall TL+CH channel coherence.

Only the selected TL generation is published to the validated snapshot / MT4 layer.

## 6. Old TL removal

Creating a new TL does not automatically erase the old TL from lifecycle history.

An old TL becomes display-retirable only when:

1. a new Turn / new high or low has been confirmed,
2. a replacement TL has been established, and
3. the old TL has no remaining current structural role.

If the line is still referenced by another tracked structural level, it is not treated as structurally ended solely because one role changed.

For Normal Run display output, the final validated result is reduced to the fixed visible generation limit in Section 7.

## 7. Maximum visible generations

Keep at most:

```text
current TL
+
immediately previous TL
```

Under Normal Run these identities mean:

- `current` = current valid TL generation reconstructed from closed-bar history in the present run.
- `previous` = the valid TL generation established immediately before `current` in that same reconstruction.

Example reconstructed sequence:

```text
TL_001 -> TL_002 -> TL_003
```

Final Normal Run display:

```text
TL_003 = current
TL_002 = previous
TL_001 = retired from MT4 display
```

The child CH and Zones follow the same parent-generation display retirement operation.

If no prior valid generation can be established from available history, `current` alone may be displayed. `previous` must not be fabricated.

## 8. Cross-structure retention

A single geometric line may still have meaning in another tracked structural level.

Example:

```text
TL_010
LARGE_DOW = replaced
MID_DOW   = active
```

Result: do not treat the line as structurally ended solely because the Large-Dow role ended.

The Normal Run rebuild must resolve the final structural references before the validated two-generation display result is produced.

## 9. CH-only update

CH may be re-positioned without changing TL when:

- the parent TL remains structurally valid,
- CH break is confirmed by the provisional CH-break detector,
- a new outer high/low subsequently confirms the new opposite-side extreme.

The updated CH remains parallel to the same TL. This operation must not create a new TL generation.

CH remains a child of its parent TL generation. Therefore current and previous TL generations may each carry their corresponding CH in the final validated drawing state.

## 10. Zone lifecycle

- `TL_ZONE` follows the parent TL.
- `CH_ZONE` follows the current CH associated with that TL.
- retiring the parent TL retires both Zones from display.
- CH-only movement moves the CH Zone with CH while preserving the TL-Zone-derived width.

## 11. History contract

Display deletion must be auditable later. The architecture must remain compatible with a lifecycle record such as:

```text
symbol
timeframe
structure_level
old_line_id
new_line_id
reason
old_anchor
new_anchor
changed_at
```

Recommended reason codes for later implementation:

- `NEW_TURN_CONFIRMED`
- `NEW_TL_SELECTED`
- `STRUCTURAL_ROLE_ENDED`
- `GENERATION_LIMIT_RETIRED`
- `CH_REPOSITIONED`

These reason-code names are implementation suggestions, not NODA Engine rules.

Normal Run history reconstruction may rebuild lifecycle generations without having persisted every event at the time it originally occurred. The reconstructed generation order is authoritative for selecting final `current` and `previous` display generations.

## 12. Closed-bar requirement

Lifecycle transitions that depend on Turn, new high/low, or structural reclassification use **closed bars only**. An unfinished candle cannot promote a replacement TL.

## 13. Normal Run safe-replacement boundary

This Lifecycle document does not authorize deletion of the last valid MT4 drawing before a new Normal Run result is validated.

The required operating sequence is defined by `docs/DRAWING_OPERATION_V1.md`:

```text
history acquisition
 -> chronological rebuild
 -> current / previous determination
 -> snapshot generation
 -> snapshot validation PASS
 -> replace owned NCA_DRAW__ objects
```

If rebuild or validation fails, the last valid MT4① drawing remains unchanged. Objects outside the `NCA_DRAW__` managed identity must not be modified.
