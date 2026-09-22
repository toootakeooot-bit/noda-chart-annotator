# NVT9 TL Audit Evidence Sidecar V01

Audit ID: ID10IQ200

## Purpose

`tools/nvt/build_nvt9_tl_audit_evidence.py` reconstructs the missing per-TL audit evidence needed by the Stage-1 TL Quality Auditor without changing the existing NVT9 generation pipeline.

The intended flow is:

```
Existing state TL
  + closed OHLC
  -> existing Turn detector
  -> existing ChannelCandidate generation
  -> exact state-geometry join
  -> evidence sidecar
  -> TL Quality Auditor
```

This tool does **not**:
- select a replacement TL,
- mutate lifecycle state,
- change Production Normal Run,
- write MT4 objects,
- infer Cross-TF ownership.

## Evidence recovered per joined TL

The sidecar reuses the existing NVT detector/candidate logic and recovers:

- Candidate ID
- Anchor1 / Anchor2 kind, time, price
- Pivot confirmation time/index
- Pivot retracement (38% confirmation data)
- decision HL identity
- HL break time and mode
- `break_by_close`
- slope
- `turn_span`
- TL contacts
- CH contacts
- `unbroken_close`
- CH anchor
- CH offset
- zone width
- direct full-history Selector candidate
- Selector classifier reason

The recovered record is passed to `tl_quality_auditor.audit_line()`, so a line with complete evidence can move from conservative `HOLD / PARTIAL` to an evidence-backed `GOOD / READY` when all structural gates actually pass.

## Geometry join

A state TL is matched to a reconstructed candidate by:

- direction,
- Anchor1 time and price,
- Anchor2 time and price.

CH offset and zone width are then used to deterministically order multiple exact-anchor variants.

Join status is reported as:

- `EXACT_UNIQUE`
- `EXACT_AMBIGUOUS`
- `NOT_FOUND`

`NOT_FOUND` is a conservative HOLD diagnostic. It is not automatically treated as an invalid TL because previous/history states can reflect an earlier replay prefix rather than the final full-history candidate pool.

## Selector evidence scope

The sidecar runs the existing full-history `select_large_mid()` and records:

- direct selected Candidate ID,
- whether a CURRENT line matches that direct selection,
- the existing classifier reason.

For `PREVIOUS` and `HISTORY` lifecycle rows, final full-history selector mismatch is **not** treated as a failure. Those rows may have been legitimate selections at earlier chronological prefixes.

## Output schema

`nvt9-tl-audit-evidence/1.0`

Top-level fields include:

- status
- line_count
- candidate_join_counts
- quality_counts
- readiness_counts
- missing_inputs
- timeframes
- evidence_contract
- production_writeback=false
- mt4_object_writeback=false
- state_mutated=false

Each line contains:

- state geometry
- reconstructed Candidate
- up to five same-anchor Candidate variants
- Selector evidence
- state/Candidate consistency checks
- embedded TL Quality audit result

## Usage

```
python tools/nvt/build_nvt9_tl_audit_evidence.py \
  --symbol "USDJPY#" \
  --state path/to/NVT9_USDJPY_DEEP_LIFECYCLE_STATE_0919.json \
  --input-dir path/to/nvt_input \
  --input-prefix NVT \
  --include-history \
  --output path/to/NVT9_TL_AUDIT_EVIDENCE.json
```

For current + previous only, omit `--include-history`.

## Current boundary

This sidecar recovers line-local evidence. Cross-timeframe ownership remains a separate evidence domain and should be joined from the NVT9 ownership / Cross-TF review artifacts.

The next integration gate is:

1. build deep lifecycle state,
2. build TL evidence sidecar,
3. join ownership evidence,
4. run TL Quality Auditor,
5. measure READY coverage,
6. only after stable held-out replay consider Stage-2 automatic re-selection.

No Stage-2 automatic correction is enabled by this tool.
