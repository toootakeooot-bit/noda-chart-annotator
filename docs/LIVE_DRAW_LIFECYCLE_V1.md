# NCA Live Draw Lifecycle v1

Status: **FIXED CONTRACT**

This document fixes how TL-centered draw objects are added, retained, replaced, and removed. CH and Zones inherit their lifecycle from the parent TL unless explicitly noted.

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

## 3. Break is observational, not replacement

A break event alone does not redraw or delete.

```text
ACTIVE
  -> break observed
BROKEN_WAIT_TURN
```

While `BROKEN_WAIT_TURN`:

- keep the old TL visible,
- keep its CH and Zones visible unless another independent display-safety rule requires otherwise,
- do not generate a replacement TL solely because of the break,
- continue observing until a new Turn confirms a new high or low.

## 4. New TL creation

A new TL may be created only after the structural sequence below:

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

## 5. TL selection occurs inside generation

Do not expose a pool of unresolved TL candidates as normal Live output.

The generator may temporarily evaluate multiple anchor combinations internally. Selection must consider:

- anchor relation,
- TL-side reaction,
- CH-side reaction,
- overall TL+CH channel coherence.

Only the selected TL is published to the Live Snapshot / MT4 layer.

## 6. Old TL removal

Creating a new TL does not automatically erase the old TL.

An old TL becomes removable only when:

1. a new Turn / new high or low has been confirmed,
2. a replacement TL has been established, and
3. the old TL has no remaining current structural role.

If the line is still referenced by either Large-Dow or Mid-Dow structure, it is not immediately removed.

## 7. Maximum visible generations

Keep at most:

```text
current TL
+
immediately previous TL
```

Example:

```text
TL_001 = previous-previous
TL_002 = previous
TL_003 = current
```

When `TL_003` is established:

- `TL_003` -> `ACTIVE`
- `TL_002` -> `PREVIOUS`
- `TL_001` -> `RETIRED` and removed from the MT4 display

The child CH and Zones follow the same retirement operation.

## 8. Cross-structure retention

A single geometric line may still have meaning in another tracked structural level.

Example:

```text
TL_010
LARGE_DOW = replaced
MID_DOW   = active
```

Result: do not retire the line solely because the Large-Dow role ended.

Only after all active structural references end may the line be retired from display, subject to the two-generation display rule.

## 9. CH-only update

CH may be re-positioned without changing TL when:

- the parent TL remains structurally valid,
- CH break is confirmed by the provisional CH-break detector,
- a new outer high/low subsequently confirms the new opposite-side extreme.

The updated CH remains parallel to the same TL. This operation must not create a new TL generation.

## 10. Zone lifecycle

- `TL_ZONE` follows the parent TL.
- `CH_ZONE` follows the current CH associated with that TL.
- retiring the parent TL retires both Zones.
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

## 12. Closed-bar requirement

Lifecycle transitions that depend on Turn, new high/low, or structural reclassification use closed bars only. An unfinished candle cannot promote a replacement TL.
