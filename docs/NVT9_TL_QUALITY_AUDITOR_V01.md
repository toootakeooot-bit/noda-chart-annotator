# NVT9 TL Quality Auditor V01

Audit ID: ID10IQ200

## Purpose

`tools/nvt/tl_quality_auditor.py` is an audit-only layer for generated trend lines (TLs).

It is intentionally downstream of the existing NVT9 generation path:

```
OHLC
  -> Pivot
  -> Candidate
  -> Selector
  -> TL Quality Auditor
  -> Ownership / Lifecycle
  -> Renderer
```

Stage 1 does **not** change Candidate, Selector, Lifecycle, Renderer, MT4 objects, or Production Normal Run behavior.

The output classification is:

- `GOOD`: core structural evidence passes and no blocking audit finding exists.
- `HOLD`: no hard failure, but evidence is incomplete or a transition/ownership state is unresolved.
- `BAD`: an explicit invalid condition exists, with the failing processing layer identified.

`Confidence` describes confidence in the classification, not whether the TL is desirable.

## Core policy

Historical matches are supporting evidence only. They may raise confidence after structural gates pass, but they never override a failed hard gate.

The main hard/transition rules are:

- Pivot anchors use the existing 38% confirmation concept.
- Wick-only penetration is not a confirmed structural break.
- Closed-bar break evidence is required where a structural break is used.
- After an active TL breaks, the next TL is not immediately promoted. A `NO-LINE / HOLD` state is allowed until the next structure is ready.
- Small-Dow evidence alone cannot promote a new Large/Mid major TL.
- A valid older structure cannot be displaced only because another TL is newer.
- `source_tf` and `owner_tf/display_tf` are distinct; Cross-TF transfer requires ownership evidence.
- Candidate-generation, Selector, Ownership/Lifecycle and Renderer failures are attributed separately.

## Pattern registry

The canonical Stage-1 pattern metadata is stored in:

`nvt/manifests/NVT9_TL_QUALITY_PATTERNS_V01.json`

Initial patterns:

- P01 normal major TL
- P02 outer TL preferred
- P03 inner TL over-selected
- P04 no-line state after break
- P05 next TL after new Dow confirmation
- P06 wick-only break
- P07 closed-bar break
- P08 Cross-TF ownership confirmed
- P09 Cross-TF ownership unresolved
- P10 reference-retained lifecycle
- P11 re-anchored current line
- P12 Selector error with valid candidate present
- P13 required candidate absent
- P14 Small-Dow promoted to major TL
- P15 latest-only precedence

## Historical teacher roles

Stage-1 regression semantics are fixed as:

- 2026-09-19: normal baseline. Expected representative result is `GOOD`.
- 2026-09-12: Outer/Inner selection case. Inner over-selection must be detected as `BAD / OUTER_STRUCTURE_MISMATCH`.
- 2026-09-05: post-break transition case. Until the next structure is complete, the result must be `HOLD / NO_LINE_HOLD`.

These cases are used as semantic regression targets, not image-similarity templates.

## Input contract

The auditor accepts a JSON object, an array, or a wrapper containing one of:

- `lines`
- `records`
- `selected_lines`
- `objects`
- `candidates`

A line record may contain the existing NVT candidate geometry fields plus audit evidence.

Common fields:

```json
{
  "line_id": "NCA_USDJPY#_H4_MID_DOW_G003",
  "direction": "FALLING",
  "source_tf": "H4",
  "owner_tf": "D1",
  "structure_level": "MID_DOW",
  "anchor1": {
    "kind": "HIGH",
    "time": "2026-01-01T00:00:00",
    "price": 160.0,
    "confirmed_by_time": "2026-01-02T00:00:00",
    "retracement": 0.38
  },
  "anchor2": {
    "kind": "HIGH",
    "time": "2026-02-01T00:00:00",
    "price": 158.0,
    "confirmed_by_time": "2026-02-02T00:00:00",
    "retracement": 0.38
  },
  "turn_span": 10,
  "tl_contacts": 3,
  "unbroken_close": true,
  "structure": {
    "hl_exists": true,
    "n_pattern_confirmed": true,
    "dow_confirmed": true,
    "hl_break": true,
    "break_by_close": true
  },
  "outer_inner": {
    "outer_candidate_exists": true,
    "selected_outer": true
  },
  "cross_tf": {
    "mapping_allowed": true,
    "owner_confirmed": true
  },
  "candidate": {
    "candidate_present": true
  },
  "selector": {
    "selector_match": true,
    "reason": "..."
  }
}
```

Missing evidence is conservative: the auditor returns `HOLD` when it cannot establish the required core evidence. It does not invent teacher truth.

## Output contract

Each line receives:

- `TL_ID`
- `Quality`
- `Confidence`
- `cause_layer`
- per-block checks for Pivot, Anchor, Structure, HL Break, Geometry, Outer/Inner, Cross-TF and History Match
- `matched_patterns`
- structured `reasons`
- source evidence snapshot

Example:

```json
{
  "TL_ID": "D1_DOWN_03",
  "Quality": "BAD",
  "Confidence": "HIGH",
  "cause_layer": "ANCHOR",
  "checks": {
    "Pivot": "PASS",
    "Anchor": "PASS",
    "Structure": "PASS",
    "HL Break": "PASS",
    "Geometry": "PASS",
    "Outer/Inner": "FAIL",
    "Cross-TF": "PASS",
    "History Match": "PASS"
  },
  "reasons": [
    {
      "pattern_id": "P03",
      "layer": "ANCHOR",
      "reason_code": "OUTER_STRUCTURE_MISMATCH",
      "disposition": "BAD"
    }
  ]
}
```

## Command-line use

```
python tools/nvt/tl_quality_auditor.py \
  --input path/to/tl_records.json \
  --output path/to/tl_quality_audit.json
```

The command writes only the audit output file.

## Regression test

Run:

```
python tests/selftest_nvt9_tl_quality_auditor.py
```

The test covers:

- 9/19 baseline -> GOOD
- 9/12 inner-TL problem -> BAD
- 9/5 NO-LINE transition -> HOLD
- wick-only break
- confirmed and ambiguous Cross-TF ownership
- Candidate-generation vs Selector attribution
- Small-Dow major promotion prohibition
- latest-only precedence prohibition
- invalid Pivot
- deterministic repeated output
- batch GOOD/HOLD/BAD counts

The test is also included in `.github/workflows/nvt9-research-ci.yml`.

## Stage 2 boundary

Do not start automatic correction until Stage 1 is stable on historical replay and held-out charts.

The future Stage-2 loop is:

```
BAD
  -> identify cause layer
  -> reevaluate Candidate / Selector as applicable
  -> produce proposed replacement
  -> re-audit
```

That loop must remain separate from the Stage-1 audit result so the system can always preserve the original decision and its failure evidence.
