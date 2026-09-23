# NVT9 TL Quality Stage-1 Gate V01

Audit ID: ID10IQ200

## Purpose

`tools/nvt/evaluate_nvt9_tl_quality_stage1_gate.py` is the final Stage-1 readiness gate before any Stage-2 automatic re-selection design is allowed.

It does **not** enable automatic re-selection.

It answers only:

> Is the Stage-1 audit evidence complete and stable enough that Stage-2 design can begin safely?

The gate evaluates the ownership-joined TL Quality output plus the real-history replay.

## Default target

Default scope is CURRENT TL only.

PREVIOUS and historical lifecycle rows are excluded because:
- they may legitimately reflect earlier chronological prefixes,
- final full-history Candidate joins may be unavailable,
- Stage-2 automatic correction will operate on the current active decision surface first.

`--all-generations` exists for stricter research runs.

## Per-line requirements

Every target CURRENT TL must satisfy all of the following:

- `Quality == GOOD`
- `AuditReadiness == READY`
- `OwnershipReadiness == PASS`
- `match_status == EXACT_UNIQUE`
- `owner_confirmed == true`
- `ownership_ambiguous != true`
- `parent_family_unresolved != true`
- no HOLD/BAD finding remains in the final audit

There is no pass-percentage threshold.

One blocked CURRENT TL blocks Stage-1.

## Historical requirements

The history replay must be supplied and must contain:

- GT_0004
- GT_0005
- GT_0006
- GT_0007
- USER_0905_TRANSITION adjudication

In addition:

- `unresolved_evidence_gaps` must be empty
- 09/05 transition exact replay geometry must be locked
- unresolved history conflicts are not allowed
- explicitly SUPERSEDED/RESOLVED old interpretations are allowed

This means the known 09/12 GT_0005 supersession is not itself a blocker because the old NO-LINE probe is retained as superseded evidence.

## Status

### PASS_STAGE1_READY_FOR_STAGE2_DESIGN

All CURRENT line gates and history gates pass.

This status means only:

> Stage-2 design and held-out testing may begin.

It does **not** mean:
- automatic Candidate replacement is enabled,
- Production can be changed,
- MT4 writeback is enabled.

`automatic_reselection_enabled` remains false.

### BLOCKED_STAGE1

Any current-line or history gate fails.

The output identifies exact failure codes.

## Line failure codes

Possible codes include:

- QUALITY_NOT_GOOD
- CORE_AUDIT_NOT_READY
- OWNERSHIP_NOT_PASS
- CANDIDATE_JOIN_NOT_EXACT_UNIQUE
- OWNER_NOT_CONFIRMED
- OWNERSHIP_AMBIGUOUS
- PARENT_FAMILY_UNRESOLVED
- AUDIT_HAS_NON_GOOD_FINDING

## History failure codes

Possible codes include:

- HISTORY_REPLAY_NOT_SUPPLIED
- REQUIRED_HISTORY_CASES_MISSING
- HISTORY_EVIDENCE_GAPS_REMAIN
- 0905_EXACT_GEOMETRY_NOT_LOCKED
- 0905_TRANSITION_ADJUDICATION_MISSING
- HISTORY_CONFLICT_UNRESOLVED

## Why parent-family unresolved blocks Stage-2

`HIGHER_TF_OWNER_PARENT_UNRESOLVED` is sufficient for Stage-1 ownership interpretation: the higher timeframe placement itself can be accepted.

However Stage-2 automatic re-selection may suppress, replace, or rank families. Without the exact parent-family identity, automatic correction can damage valid retained references.

Therefore:

- TL Quality Ownership check may PASS
- Stage-1-to-Stage-2 gate remains BLOCKED

until parent-family identity is resolved.

## Why EXACT_AMBIGUOUS blocks Stage-2

The evidence sidecar can deterministically choose a canonical candidate among multiple exact-anchor variants for audit purposes.

That is acceptable for Stage-1 inspection.

It is **not** sufficient for automatic replacement logic. Stage-2 must know exactly which candidate object/family it is correcting.

Therefore Stage-2 requires:

`match_status == EXACT_UNIQUE`

## 09/05 current implication

The registered user adjudication currently states:

`ACTIVE_TL -> NO_LINE_HOLD -> NEXT_TL_ACTIVE`

but exact replay geometry was intentionally left unlocked.

Until the 09/05 exact anchors/geometry are frozen and replayed, this gate must return:

`BLOCKED_STAGE1`

with:

`0905_EXACT_GEOMETRY_NOT_LOCKED`

This prevents semantic understanding from being mistaken for a fully reproducible regression test.

## Usage

```
python tools/nvt/evaluate_nvt9_tl_quality_stage1_gate.py \
  --ownership-join path/to/NVT9_TL_QUALITY_OWNERSHIP_JOIN.json \
  --history-replay path/to/NVT9_TL_QUALITY_HISTORY_REPLAY.json \
  --output path/to/NVT9_TL_QUALITY_STAGE1_GATE.json
```

Optional stricter research mode:

```
--all-generations
```

## Safety

The evaluator has no write path to:
- Candidate selection
- lifecycle state
- renderer
- MT4
- Production Normal Run

Stage-2 automatic correction remains disabled regardless of PASS/BLOCKED status.
