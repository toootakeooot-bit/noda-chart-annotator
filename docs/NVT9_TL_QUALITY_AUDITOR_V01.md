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

`nvt/manifests/NVT9_TL_QUALITY_PATTERNS_V02.json` (V01 is retained as the initial registry)

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


## Real-history replay

Stage 1 now includes a separate real-history replay builder:

`tools/nvt/build_nvt9_tl_quality_history_replay.py`

It intentionally separates:

1. teacher / user-adjudicated expectation,
2. generated candidate or TL Quality,
3. audit evidence readiness.

This prevents a teacher-history match from forcing a generated TL to GOOD when the line-level evidence contract is incomplete.

Historical cases currently registered:

- GT_0004 / 2026-09-05 D1: persistent original rising reference (`P16`).
- USER_0905_TRANSITION / 2026-09-05 H1/M15: post-break NO-LINE/HOLD transition (`P04`), semantic-only until exact geometry is frozen.
- GT_0005 / 2026-09-12 H1: valid but display-suppressed TURN_LINE (`P17`).
- GT_0006 / 2026-09-12 H1: gentler-angle selector preference (`P18`); absent approximate anchor-window candidate is diagnostic HOLD (`P19`), not hard BAD.
- NVT8 2026-09-19 held-out: strict held-out teacher assertions may be used as global context, but do not force unrelated current cross-TF line IDs to GOOD.
- GT_0007 / 2026-08-08 H1: parent NO-LINE with M15 ownership (`P20`).

The replay also detects evidence supersession. In particular, the older NVT5 GT_0005 probe interpreted the case as NO-LINE, while the later reviewed GT_0005 Ground Truth explicitly states that the turn line is structurally valid but intentionally display-suppressed. The old probe remains visible as superseded evidence.

Example:

```
python tools/nvt/build_nvt9_tl_quality_history_replay.py \
  --teacher-anchor-probe path/to/NVT5_TEACHER_ANCHOR_PROBE_USDJPY.json \
  --cross-tf-0919 path/to/NVT9_USDJPY_CROSS_TF_0919.json \
  --strict-heldout-0919 path/to/NVT8_STRICT_HELDOUT_COMPARISON_CORRECTED.json \
  --output path/to/NVT9_TL_QUALITY_HISTORY_REPLAY.json
```

### AuditReadiness

Every generated-line audit now also exposes:

- `READY`: the core Pivot / Anchor / Structure / HL-break evidence is present.
- `PARTIAL`: some core evidence is present, but one or more required blocks are missing.
- `INSUFFICIENT`: core line-level evidence is largely unavailable.

`missing_evidence` lists the blocks that must be persisted before the line can receive a high-quality automatic judgment.

For the existing 09/19 cross-timeframe review artifact, anchor geometry and ownership-comparison data are persisted, but all per-line 38% confirmation, HL/N/Dow state and closed-bar break evidence are not co-located in that artifact. The real-history replay therefore must not upgrade those lines to GOOD merely because strict NVT8 passed elsewhere.

### Next evidence-contract gate

Before Stage 2 automatic correction, the live/history artifact should persist per TL:

- anchor retracement / Pivot confirmation,
- HL identity and price,
- N / Dow structure state,
- break event and `break_by_close`,
- Candidate rank,
- Selector reason,
- source timeframe and ownership evidence,
- lifecycle / display role.

Then rerun the real-history replay and measure READY coverage before enabling any BAD -> reselect -> re-audit loop.
