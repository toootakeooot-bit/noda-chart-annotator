# NVT9 TL Quality Ownership Join V01

Audit ID: ID10IQ200

## Purpose

`tools/nvt/build_nvt9_tl_quality_ownership_join.py` joins the per-line structural evidence sidecar with the existing NVT9 cross-timeframe ownership adjudication.

This completes the Stage-1 audit chain:

```
OHLC
 -> Pivot / Candidate / Selector
 -> lifecycle state
 -> TL audit evidence sidecar
 -> ownership adjudication join
 -> TL Quality Auditor
 -> GOOD / HOLD / BAD
    + core AuditReadiness
    + OwnershipReadiness
```

The join is audit-only. It does not reselect a line, mutate lifecycle state, alter MT4 objects, or change Production Normal Run.

## Ownership classifications

### PARENT_OWNED_SAME_FAMILY

The source-TF line is confirmed to belong to a higher timeframe and the matching parent-family line is identified.

Audit behavior:
- `owner_tf = structural_owner_tf`
- `owner_confirmed = true`
- `parent_family_confirmed = true`
- Cross-TF = PASS
- P08 may match

### HIGHER_TF_OWNER_PARENT_UNRESOLVED

Teacher/manual evidence confirms the higher structural owner timeframe, but the exact retained parent-family line is not yet identified.

Audit behavior:
- higher `owner_tf` is accepted
- `owner_confirmed = true`
- `parent_family_unresolved = true`
- Cross-TF = PASS for timeframe ownership
- exact parent-family suppression/replacement remains blocked elsewhere

This deliberately separates **timeframe ownership** from **exact parent-family identity**.

### LOCAL_OWNED_DISTINCT

The line is explicitly confirmed as a source-timeframe-local structure.

Audit behavior:
- `owner_tf = source_tf`
- `owner_confirmed = true`
- Cross-TF = PASS
- P21 `LOCAL_OWNER_CONFIRMED` matches

### AMBIGUOUS_KEEP_VISIBLE

Ownership is unresolved. The source timeframe remains the runtime/display fallback only so the line is not hidden prematurely.

Audit behavior:
- `owner_tf = source_tf` for fallback visibility
- `owner_confirmed = false`
- `ownership_ambiguous = true`
- Cross-TF = HOLD
- P09 `OWNERSHIP_UNRESOLVED`
- the underlying TL is not made structurally BAD solely because ownership is unresolved

This fixes the previous ambiguity where `source_tf == owner_tf` could accidentally look like confirmed local ownership.

### D1 root ownership

D1 has no higher parent in the supported D1/H4/H1/M15 hierarchy.

If a D1 line has no child-to-parent ownership adjudication row, the join records:

- `classification = ROOT_LOCAL_OWNED`
- `owner_tf = D1`
- confirmed native/root ownership
- P21

A missing ownership record on H4/H1/M15 remains HOLD instead of being assumed local.

## Gate interaction

An optional V3.5 ownership-gate JSON may be supplied.

Per-line gate effects:
- `unresolved` keeps the line ownership ambiguous
- `problems` prevents confirmation and keeps the line HOLD
- `parent_match_unresolved` does not revoke a teacher-confirmed higher owner timeframe; it marks only the exact parent-family relation unresolved

A globally blocked gate does not downgrade unrelated lines. The join is line-specific.

## Auditor change

`tl_quality_auditor.py` now evaluates explicit ownership evidence before source/owner equality.

Therefore:

```
source_tf=H4
owner_tf=H4
classification=AMBIGUOUS_KEEP_VISIBLE
owner_confirmed=false
ownership_ambiguous=true
```

is correctly:

```
Quality=HOLD
Cross-TF=HOLD
OwnershipReadiness=HOLD
reason=OWNERSHIP_UNRESOLVED
```

rather than an accidental PASS.

## Output

Schema:

`nvt9-tl-quality-ownership-join/1.0`

Top-level summary includes:
- quality_counts
- core_readiness_counts
- ownership_readiness_counts
- ownership_classification_counts
- owner_tf_counts
- ownership_unresolved_count

Each TL retains:
- pre-ownership audit
- ownership evidence
- final quality audit
- ownership delta

## Usage

```
python tools/nvt/build_nvt9_tl_quality_ownership_join.py \
  --evidence path/to/NVT9_TL_AUDIT_EVIDENCE.json \
  --ownership path/to/NVT9_USDJPY_OWNERSHIP_ADJUDICATION.json \
  --gate path/to/NVT9_USDJPY_OWNERSHIP_GATE.json \
  --output path/to/NVT9_TL_QUALITY_OWNERSHIP_JOIN.json
```

`--gate` is optional.

## 09/19 historical implication

The saved 09/19 automatic adjudication contains six non-D1 records and all six are `AMBIGUOUS_KEEP_VISIBLE`; no automatic exact-geometry ownership was resolved in that artifact.

Therefore the correct historical replay behavior is:
- D1: native/root ownership may PASS
- H4/H1/M15 lines: remain visible but Ownership=HOLD until teacher/manual ownership confirmation is supplied
- do not freeze H4->D1, H1->H4, M15->H1 solely from the earlier equal-window observation

## Next gate

Before Stage-2 automatic re-selection:

1. run the per-TL evidence sidecar,
2. join final ownership adjudication,
3. measure `AuditReadiness=READY` and `OwnershipReadiness=PASS`,
4. replay 09/19, 09/12 and 09/05,
5. keep unresolved ownership visible,
6. only then design BAD -> alternate Candidate -> re-audit.

Automatic correction remains disabled.
