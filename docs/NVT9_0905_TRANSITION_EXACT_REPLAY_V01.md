# NVT9 09/05 Transition Exact Replay V01

Audit ID: ID10IQ200

## Purpose

This stage converts the user-adjudicated 09/05 transition semantics

`ACTIVE_TL -> NO_LINE_HOLD -> NEXT_TL_ACTIVE`

into a deterministic, time-frozen replay artifact.

It does **not** lock teacher-video Ground Truth anchors.

## Tool

`tools/nvt/build_nvt9_0905_transition_exact_replay.py`

Inputs:
- `NVT_USDJPY#_H4.csv`
- `NVT_USDJPY#_H1.csv`

Cutoff:
- `2026-09-05T00:00:00` exclusive

Selection horizon:
- last 600 pre-cutoff bars

Detector/history horizon:
- all available pre-cutoff bars

All post-cutoff bars are excluded from selection, transition detection and retained-reference validation.

## H4 lock requirement

H4 passes only when replay proves:

1. effective state = `TRANSITION_NO_TL`
2. an actual prior activated TL candidate exists
3. that prior TL has a closed-bar break before cutoff
4. no unbroken replacement N is active
5. chronological retained-reference fallback is **not** used after this explicit break

Therefore a simple absence of candidates is not sufficient to lock the 09/05 H4 middle state.

## H1 lock requirement

H1 passes only when the effective family is one of:

- `ACTIVE`
- `NEW_ACTIVE`
- `REFERENCE_RETAINED`

and an exact Candidate ID/geometry is available.

For ACTIVE / NEW_ACTIVE:
- existing N Candidate rules must have produced the family
- decision-HL activation must be closed-bar based

For REFERENCE_RETAINED:
- the 600-bar rolling window may contain no newly selectable N
- full pre-cutoff chronological replay must identify the retained line
- the retained line must join back to an exact Candidate
- it must remain `unbroken_close=true`
- retention is forbidden when the rolling transition explicitly detects `OLD_TL_BROKEN_NO_UNBROKEN_REPLACEMENT_N`

## M15

M15 transition geometry is not independently reselected in this lock.

The certified display contract is:

- M15 native selector disabled
- M15 display owner = H1
- copy the exact H1 locked geometry without destination reselection

## Fingerprints

The artifact stores SHA-256 fingerprints for:

- complete pre-cutoff H4/H1 OHLC
- rolling 600-bar H4/H1 windows

This makes the exact replay tied to a concrete input history.

## PASS output

`PASS_0905_TRANSITION_EXACT_REPLAY`

with:

`transition_exact_geometry_locked=true`

This means the H4/H1 transition-state geometry is mechanically reproducible from the frozen inputs.

It explicitly also writes:

`teacher_ground_truth_exact_anchors_locked=false`

because GT_0004 D1 teacher anchors remain a separate Ground Truth problem.

## History Replay handoff

`build_nvt9_tl_quality_history_replay.py` accepts:

```
--transition-lock-0905 path/to/NVT9_0905_TRANSITION_EXACT_REPLAY.json
```

The original semantic adjudication file remains unchanged.

History Replay marks the 09/05 transition exact geometry as locked only when the supplied artifact has:

- expected schema
- exact 09/05 case date
- exact cutoff
- PASS status
- outer and inner lock flags true
- zero failed checks

Malformed or BLOCKED artifacts cannot unlock Stage-1.

## Host runner

Run:

`setup\RUN_NVT9_0905_EXACT_TRANSITION.cmd`

It reads the existing MT4 Common Files `nvt_input` folder and writes:

`live_output\nvt9_0905_exact_transition\NVT9_0905_TRANSITION_EXACT_REPLAY.json`

No source manifest or Ground Truth is mutated.

## Stage-1 consequence

A valid transition lock removes the specific Stage-1 blocker:

`0905_EXACT_GEOMETRY_NOT_LOCKED`

It does not bypass:
- current-line Quality failures
- Candidate join ambiguity
- ownership ambiguity
- unresolved parent-family identity
- any other history evidence gap

Automatic re-selection remains disabled.
