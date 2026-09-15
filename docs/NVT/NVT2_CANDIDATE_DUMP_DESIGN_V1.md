# NVT2 Candidate Dump Design v1

Status: **FIXED FOR NVT2 IMPLEMENTATION**  
Fixed date: 2026-09-15

## 1. Purpose

NVT2 exposes the complete candidate pool produced by the current NCA detector/geometry path at a frozen historical cutoff.

The goal is to answer, for each teacher Ground Truth case:

1. Did the teacher line exist anywhere in the NCA candidate pool?
2. If yes, which candidate facts distinguish it from the candidate currently selected by NCA?
3. If no, the failure belongs upstream in Market Facts / candidate generation rather than Teacher Selector scoring.

NVT2 is read-only research tooling. It must not alter production `tools/live_draw/` behavior.

## 2. Inputs

Required:

```text
--input-csv   NCA/NVT closed-bar OHLC CSV
--symbol      canonical broker symbol, e.g. USDJPY#
--timeframe   D1 | H4 | H1 | M15
--output      output JSON path
```

Optional:

```text
--cutoff      ISO-8601 timestamp; bars after cutoff are excluded
```

If no cutoff is supplied, the whole CSV is used. Hard Ground Truth regression still requires a frozen cutoff under NVT5.

## 2A. Ground-Truth-required execution matrix

The NVT2 corpus runner must process the **source/timeframe pairs actually required by registered Ground Truth cases**.

It must not require every source video to have every `D1/H4/H1/M15` history file merely because those are the production Normal Run timeframes.

Reason:

```text
Ground Truth case -> source_id + timeframe
                   -> only that source/timeframe candidate pool is a required NVT2 gate
```

An optional timeframe history gap must not block an unrelated Ground Truth comparison.

Example: if the current registered cases require D1/H4/H1 only, insufficient M15 depth for an older source date is recorded as an optional research limitation, not as an NVT2 failure for the D1/H4/H1 cases.

When a future Ground Truth case explicitly requires that missing timeframe, the missing history becomes a real gate and must be acquired before that case can pass NVT2.

## 3. Production components reused without modification

```text
load_ohlc_csv
 -> detect_turns
 -> build_channel_candidates
 -> select_large_mid
```

The dump must not duplicate or rewrite production candidate-generation semantics.

## 4. Per-candidate fields v1

Raw identity / geometry:

```text
candidate_id
direction
anchor1 kind/index/time/price/confirmed_by
anchor2 kind/index/time/price/confirmed_by
ch_anchor kind/index/time/price/confirmed_by
slope_per_second
absolute_slope_per_second
ch_offset
zone_width
```

Existing NCA evidence:

```text
turn_span
tl_contacts
ch_contacts
unbroken_close
selected_as_large
selected_as_mid
```

Anchor candle morphology facts:

```text
anchor1_range
anchor1_body
anchor1_upper_wick
anchor1_lower_wick
anchor1_relevant_wick
anchor1_relevant_wick_fraction
anchor2_...
ch_anchor_...
```

`relevant_wick` means lower wick for a LOW pivot and upper wick for a HIGH pivot. This is a factual measurement only; NVT2 does not decide whether the wick is noise.

## 5. Summary fields

Each dump records:

```text
schema
symbol
timeframe
cutoff
closed_bar_count
first_bar_time
last_bar_time
confirmed_turn_count
candidate_count
selected_large_candidate_id
selected_mid_candidate_id
classifier_audit
candidates[]
```

The corpus runner also records which Ground Truth case IDs depend on each source/timeframe dump.

## 6. Explicit non-goals

NVT2 v1 does **not** yet implement:

- teacher scoring;
- cluster-right-edge scoring;
- gentler-angle preference weighting;
- persistent-reference lifecycle;
- NO-LINE decision;
- wick-noise rejection;
- multi-timeframe hierarchy scoring.

Those belong to NVT3/NVT6/NVT7 after candidate availability is measured.

## 7. Ground Truth comparison gate

For a teacher case, comparison order is fixed:

```text
Market Facts valid?
 -> teacher anchors represented by some candidate?
    NO  -> CANDIDATE_ABSENT
    YES -> NVT3 selection comparison
```

Do not tune selector weights to compensate for a missing candidate.

## 8. Historical input isolation

NVT research history is stored separately from Normal Run input:

```text
noda_draw/nvt_input
```

The NVT deep-history exporter may request more bars than the terminal currently has loaded. The actual exported count/range is authoritative; the requested count is not proof of coverage.

A Ground Truth-required source/timeframe pair must contain sufficient closed bars at or before its cutoff. Optional, currently unused timeframe gaps are non-blocking.

## 9. Production protection

NVT2 writes only research JSON under an explicitly chosen output path.

It must not:

- modify Normal Run state/snapshot;
- write `NCA_DRAW__` objects;
- change detector/geometry/lifecycle source;
- place ChatGPT in runtime execution;
- create trading authority.
