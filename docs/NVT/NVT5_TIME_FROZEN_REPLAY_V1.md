# NVT5 Time-Frozen Replay v1

Status: **FIXED**  
Fixed date: 2026-09-15

## 1. Purpose

NVT5 reproduces each teacher reference case with **only the broker OHLC that was available at the reference market cutoff**.

NVT5 is research-only. It must not modify production Normal Run state/snapshot, `tools/live_draw/` semantics, MT4 `NCA_DRAW__` objects, or any trade state.

## 2. Source-date rule for the initial USDJPY corpus

The initial five NVT videos are weekend analysis videos. Their market-data session is therefore represented by the immediately preceding normal FX market date already recorded in:

```text
nvt/manifests/USDJPY_EXPECTED_MARKET_CUTOFFS_V1.json
```

The manifest date identifies the intended market session only. It does **not** define a clock time.

## 3. Exact cutoff authority

The exact cutoff for each `source_id + timeframe` pair must be resolved from the **actual XM MT4 closed-bar history**.

For each required pair:

```text
target_market_date
 -> load NVT deep-history CSV for that timeframe
 -> select bars whose broker timestamp date == target_market_date
 -> exact_cutoff = latest closed-bar timestamp on that broker date
```

Hard rules:

- do not invent `23:59:59` as the final verified cutoff;
- do not translate the teacher video's playback timestamp into a broker market timestamp;
- do not silently fall back to a previous market date if the expected date has no exported bar;
- if the expected broker date is absent from the CSV, NVT5 must stop that pair as insufficient input;
- the exact broker timestamp is recorded in NVT5 research output before comparison.

## 4. Time-freeze rule

For an exact resolved cutoff `T`:

```text
frozen_bars = all closed bars with bar_time <= T
future_bars = all exported bars with bar_time > T
```

The frozen input must satisfy:

```text
max(frozen_bars.time) <= T
```

and the replay manifest must record:

```text
requested_cutoff
effective_last_closed_bar
first_frozen_bar
frozen_bar_count
excluded_future_bar_count
source_sha256
frozen_sha256
look_ahead_guard = PASS
```

## 5. Pair-level replay

Cases sharing the same `source_id + timeframe` share the same market cutoff and may share one frozen replay dataset.

The initial seven USDJPY Ground Truth cases currently reduce to five required replay pairs:

```text
NVT_VIDEO_20260808  D1  -> GT_0001, GT_0002
NVT_VIDEO_20260808  H1  -> GT_0007
NVT_VIDEO_20260830  H4  -> GT_0003
NVT_VIDEO_20260905  D1  -> GT_0004
NVT_VIDEO_20260912  H1  -> GT_0005, GT_0006
```

NVT5 must derive this from Ground Truth, not hard-code the list in production logic.

## 6. Exact-cutoff output

NVT5 must produce both:

```text
NVT5_REPLAY_PLAN.tsv
NVT5_RESOLVED_CUTOFFS.json
```

The resolved JSON is research evidence and is the authoritative source for tightening the provisional `market_data_cutoff` fields in Ground Truth after audit.

Ground Truth files are **not automatically rewritten by the PC runner**. Any repo Ground Truth amendment remains an audited source-data change.

## 7. Replay output

For every required pair, NVT5 creates:

```text
frozen OHLC CSV
replay manifest
exact-cutoff candidate dump
```

The candidate dump is generated from the frozen CSV, so NVT3 can later compare Teacher vs NCA without any future bars.

## 8. Ground Truth anchor discipline

NVT5 resolves market cutoffs first. It does **not** guess teacher anchors.

Exact teacher anchors may be locked only after visual/source evidence and frozen OHLC are reconciled. Until then:

```text
anchor = UNKNOWN
comparison = PENDING_GROUND_TRUTH
```

A Teacher line must not be chosen merely because it looks like the current NCA baseline selection.

## 9. NO-LINE cases

`GT_0005` and `GT_0007` are valid NVT5 cases even though they contain no Teacher object. NVT5 freezes the corresponding H1 history and preserves the NVT3 `NO_LINE_MISMATCH` evidence for later Structure Ownership / Selector work.

NVT5 does not modify the production selector to make those cases pass.

## 10. Production protection

NVT5 outputs are restricted to NVT research locations such as:

```text
MetaQuotes/Terminal/Common/Files/noda_draw/nvt_output/
```

NVT5 must keep all of the following false:

```text
production_writeback
snapshot_writeback
mt4_object_writeback
trade_authority
```

## 11. Gate to NVT6

NVT5 is ready to feed NVT6 only when:

```text
required replay pairs resolved from real broker OHLC
look-ahead guard PASS for every required pair
resolved cutoffs recorded
frozen candidate dumps generated
NO-LINE cases preserved as explicit mismatch evidence
remaining drawable Teacher cases have anchor review material available
```

NVT6 must still obey the integration rule:

```text
candidate absent -> do not patch Selector
candidate present but not selected -> Selector investigation
structure/timeframe ownership mismatch -> ownership/NO-LINE investigation before Selector scoring
```
