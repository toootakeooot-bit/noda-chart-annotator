# NVT Video First-Pass Evidence Report — 2026-09-15

Status: **DRAFT EVIDENCE / NOT PRODUCTION RULES**

Primary symbol: `USDJPY`

Source corpus:

- NVT_VIDEO_20260808
- NVT_VIDEO_20260822
- NVT_VIDEO_20260830
- NVT_VIDEO_20260905
- NVT_VIDEO_20260912

All five sources contain timed Japanese subtitles, allowing speech evidence to be aligned with chart frames.

## 1. Strong preliminary findings

### F1 — Candidate selection is not purely newest-generation selection

2026-08-08 around 10:54-11:14:

- the teacher identifies an initial channel;
- a newly updated high allows the channel to be moved/updated;
- however, the initial channel may remain because it can still serve a role as a later profit/target reference;
- too many channels should not be kept because clutter reduces usefulness.

Implication for NVT:

- `old = delete` is not sufficient;
- line retention is role-dependent;
- channel lifecycle must distinguish `still useful reference` from `obsolete`.

### F2 — Some lines are intentionally retained for reconstructability

2026-08-08 around 17:54-18:14:

- lines that are obvious from visual context need not all be drawn;
- lines whose anchors become difficult to remember when zoomed out are deliberately retained.

Implication:

- rendering is not only structure-state output;
- retained reference lines may have a memory/explanation role;
- teacher-style display may require `REFERENCE` or similar role separate from active current/previous.

### F3 — Anchor selection uses structure plus cluster-edge choice

2026-08-08 around 10:16-10:32:

- for a secondary uptrend line, the teacher describes choosing from the lowest low to the rightmost point of a cluster.

2026-09-12 around 30:50-31:18:

- the teacher again describes a technical high and a cluster-right-edge candidate set;
- redrawing to the newly raised high is also valid;
- among valid alternatives, the teacher states a preference for the gentler angle because it better captures intermediate retracements.

Implication:

- selector should enumerate multiple valid candidates rather than assume one geometrically unique line;
- `cluster right edge` and `gentler-angle preference` are candidate features for NVT6 scoring.

### F4 — Timeframe ownership matters and `NO LINE` is a valid result

2026-08-08 around 29:21-29:42:

- a line too far in the future can be kept on a higher timeframe instead of cluttering the execution timeframe;
- the teacher distinguishes the timeframe where the line is actually meaningful/visible.

2026-08-08 around 39:15-39:35:

- the teacher explicitly says an H1 line does not need to be drawn;
- if an internal line is desired, the M15 wave can be used instead.

Implication:

- a teacher-reproduction system must not force a fixed TL/CH count on every timeframe;
- timeframe-specific visibility/ownership should be modeled.

### F5 — Higher-timeframe/basic line priority precedes advanced line construction

2026-08-22 around 22:34-22:52:

- the teacher strongly prioritizes first drawing the ordinary 4H uptrend line;
- more elaborate lower-timeframe/leading-line constructions should come only after the basic higher-timeframe structure is present.

Implication:

- NVT selector may require hierarchical priority: basic/obvious structural line first, derived/advanced line second.

### F6 — Wick handling is material to line validity

2026-08-30 around 04:16-04:34:

- the teacher reviews a prior 4H uptrend line drawn wick-to-wick;
- he questions whether the wick treatment was precise enough.

2026-09-05 around 18:09-18:27:

- the teacher explicitly says that using the proper wick points would have shown the line was already broken and admits the prior handling was too approximate.

Implication:

- anchor precision cannot be reduced to candle close/body only;
- wick/body handling must be captured as explicit evidence in Ground Truth.

### F7 — Wave/turn recognition depends on actual high-low update, with internal-wave suppression

2026-08-30 around 16:27-16:50:

- the teacher says high/low wave points are counted where a clear update occurs;
- without a clear high/low break, movement remains inside one wave.

2026-08-08 includes supporting statements about 38.2% retracement and a minimum candle-count rule being used to suppress visually apparent but technically insignificant waves.

Implication:

- NVT must separately validate Market Facts / turn recognition before blaming candidate selection.

### F8 — Persistent reference versus redraw can change interpretation

2026-09-05 around 03:19-04:37:

- the teacher notices the PC chart and the long-retained mobile chart use different endpoints;
- he says the PC version is not necessarily invalid, but the retained mobile line had already been broken;
- he later states the channel should fundamentally remain aligned with its original reference position.

Implication:

- `valid alternative` and `preferred persistent reference` must be distinct concepts;
- a newer endpoint is not automatically the preferred teacher line.

## 2. Direct challenge to current NCA assumptions

The teacher evidence already suggests the future NVT model should not assume:

```text
newest valid line always replaces older line
exactly current + previous is sufficient for all visible teacher lines
every timeframe must output a line
latest high/low always defines the preferred channel
all structurally valid candidates are equivalent
```

These observations do **not** change production NCA before NVT9.

## 3. Candidate Ground Truth events for detailed visual review

Priority timestamps:

```text
2026-08-08 10:16-11:14  secondary uptrend TL + channel update/retention
2026-08-08 17:54-18:14  why a line is deliberately retained
2026-08-08 29:21-29:42  timeframe ownership / clutter control
2026-08-08 39:15-39:35  explicit H1 NO-LINE / use M15 structure
2026-08-22 22:34-22:52  higher-TF basic-line priority
2026-08-30 04:16-04:34  wick-to-wick line review
2026-08-30 16:27-17:40  wave recognition and line relationship
2026-09-05 03:19-04:40  persistent mobile line vs updated PC line
2026-09-05 18:09-18:27  wick precision / admitted prior approximation
2026-09-12 30:50-31:25  cluster-right-edge candidates + gentler-angle preference
```

## 4. Next analysis pass

For each priority event:

1. extract pre-event / action / post-event frames;
2. record symbol, timeframe and visible date range;
3. identify exact teacher objects involved;
4. mark candidate anchors by bar/time where possible;
5. label action as `ADD | KEEP | MOVE | DELETE | RECLASSIFY | NO_LINE`;
6. classify evidence as explicit teacher statement vs visual inference;
7. create DRAFT Ground Truth cases only after visual confirmation.

## 5. Current judgment

```text
VIDEO INGEST: PASS
TIMED SPEECH ALIGNMENT: PASS
USDJPY PRIMARY CORPUS: ESTABLISHED
PRELIMINARY TEACHER RULE SIGNAL: STRONG
GROUND TRUTH LOCKED: NO
NCA PRODUCTION MODIFIED: NO
NEXT: VISUAL EVENT-BY-EVENT REVIEW -> NVT1 DRAFT CASES
```
