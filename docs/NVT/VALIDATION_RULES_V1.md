# NVT Validation Rules v1

Status: **FIXED**  
Fixed date: 2026-09-15

## 1. Objective

NVT validation measures whether NCA can reproduce the teacher's observed structural drawing behavior at the same market-data cutoff.

The goal is structural reproduction, not superficial pixel similarity.

## 2. Mandatory time freeze

For every case with teacher decision cutoff T:

```text
teacher evidence at T
vs
NCA/NVT replay using bars <= T only
```

Future data after T is prohibited in that comparison.

## 3. Validation order

Always diagnose in this order:

1. candidate existence;
2. selected structure;
3. anchor choice;
4. channel construction;
5. lifecycle / keep-replace-delete behavior;
6. role classification;
7. render style.

Do not fix a later layer to compensate for an earlier-layer failure.

## 4. Candidate rule

If the teacher line is not represented by any NCA candidate within the agreed anchor tolerance, classify:

```text
CANDIDATE_ABSENT
```

Selector tuning is not permitted to hide a candidate-generation failure.

## 5. Selection rule

If the teacher line exists in the candidate pool but NCA chooses another candidate, classify:

```text
SELECTION
```

This is the primary evidence used later for Structure Selector development.

## 6. Anchor rule

Anchor comparison is performed in bar/time space first, price second.

Initial v1 reporting should record:

```text
exact-bar match
within +/-1 closed bar
outside tolerance
```

A hard acceptance tolerance is not globally fixed until NVT1/NVT3 reveal the source-image precision that is realistically available.

## 7. Channel rule

CH evaluation must be separate from TL evaluation and should compare:

- parent TL identity;
- opposite-side anchor/contact;
- direction / parallel relationship;
- channel width where measurable.

## 8. Lifecycle rule

For video or sequential evidence, compare teacher actions:

```text
ADD
KEEP
MOVE
REPLACE
DELETE
```

A line intentionally kept by the teacher is evidence even if it is not the newest line.

## 9. Forming-bar rule

Each teacher anchor should record whether it is based on:

```text
CLOSED
FORMING
UNKNOWN
```

If teacher use of forming bars is material, this becomes an explicit NVT finding. The current NCA closed-bar production rule must not be silently changed during NVT0-NVT8.

## 10. Metrics

NVT reports should separate at least:

```text
Candidate Recall
Selection Accuracy
Anchor Accuracy
Channel Accuracy
Lifecycle Accuracy
Role Accuracy
Render Accuracy
```

No single aggregate score may conceal a poor structural dimension.

## 11. Training vs validation separation

Cases used to derive selector/lifecycle rules are development cases.

NVT8 requires independent videos/cases not used to tune the rule set. Production promotion at NVT9 requires performance on this held-out evidence.

## 12. Evidence threshold discipline

One screenshot or one video event is not sufficient to create a general production rule unless it merely confirms an already fixed definition.

New behavioral rules should be supported by repeated cases across multiple market structures/timeframes before NVT9 promotion.
