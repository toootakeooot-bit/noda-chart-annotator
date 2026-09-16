# NVT1 Draft Case Registry — 2026-09-15

Status: **DRAFT CASES / VISUALLY CONFIRMED EVENT WINDOWS**

Primary symbol: `USDJPY`

This registry converts the first-pass video findings into concrete event cases. It does not yet lock exact market-bar anchors; those will be resolved during NVT2/NVT5 candidate dump + time-frozen replay.

> Amendment 2026-09-16: GT_0005 semantics were corrected after direct video review. It is a valid small-Dow turn line that is intentionally not displayed because it is steep/short-lived and would add clutter. It is **not** an ownership rejection or invalid NO-LINE case.

## Case set

| Case | Source | TF | Video window | Main observation | Draft target |
|---|---|---:|---|---|---|
| GT_0001 | 2026-08-08 | D1 | 10:16-10:34 | Secondary uptrend TL: lowest low -> rightmost edge of a cluster | anchor-selection rule |
| GT_0002 | 2026-08-08 | D1 | 10:54-11:16 | New CH can be updated to new high while original CH may remain if it still has a role | lifecycle / KEEP reference |
| GT_0003 | 2026-08-30 | H4 | 04:16-05:01 | Wick-to-wick TL reviewed; long wick may be noise, but teacher retains line provisionally | wick/noise handling |
| GT_0004 | 2026-09-05 | D1 | 03:19-04:45 | Long-retained original TL/CH preferred over a newer PC re-anchoring; original reference had already shown the break | persistent-reference preference |
| GT_0005 | 2026-09-12 | H1 | 29:48-30:29 | Valid small-Dow turn line can be drawn from valid highs, but its steep/short-lived nature and display-clutter cost lead the teacher not to draw it | valid-but-display-suppressed lifecycle case |
| GT_0006 | 2026-09-12 | H1 | 30:50-31:49 | Multiple structurally valid high/cluster candidates; teacher prefers a gentler line to capture intermediate pullbacks; long wick may be treated as noise | selector scoring / lifecycle bridge |
| OBS_0007 | 2026-08-22 | H4 -> H1 | 22:01-22:55 | Basic/ordinary H4 trend line must be established before advanced H1 leading-line techniques | hierarchy/procedure evidence |
| OBS_0008 | 2026-08-30 | H1 | 16:50-17:38 | Without a high update, movement stays internal; major line anchors follow the larger recognized wave, not every small visible pivot | Market-Facts / turn suppression |
| OBS_0009 | 2026-08-08 | D1 | 18:01-18:13 | A line may be retained because its distant origin becomes hard to reconstruct after zooming | REFERENCE display role |

## Visual confirmation completed

Frames were inspected around each high-priority event. Confirmed visible chart/timeframe examples include:

- 2026-08-08 D1: thick blue rising channel, cyan major wave, retained long-range reference lines;
- 2026-08-22 H1: lower-timeframe candidate constructions are visible before the teacher returns to the simpler higher-TF line hierarchy;
- 2026-08-30 H4: cyan channel/TL with wick-sensitive contact at the reviewed structure;
- 2026-08-30 H1: teacher markup distinguishes larger wave structure from internal movement;
- 2026-09-05 D1: original rising channel/TL remains visible while the teacher explains the PC/mobile re-anchor discrepancy;
- 2026-09-12 H1: valid-but-suppressed small-Dow turn-line semantics are discussed, then several high candidates are marked and a gentler descending mid-line is constructed.

## Evidence discipline

For each case, keep these separate:

1. `observed_reason_text`: teacher-stated explanation from subtitle/audio;
2. visible drawing state in the event frame;
3. analyst inference about how NCA may implement the behavior.

No item in this registry is a production rule. Exact anchor timestamps/prices remain `UNKNOWN` unless resolvable without guesswork.

## NVT1 acceptance state

```text
VIDEO SOURCE LOCATED: PASS
SYMBOL USDJPY: PASS
TIMEFRAME FOR CORE CASES: PASS
VIDEO EVENT WINDOWS: PASS
VISUAL EVENT CONFIRMATION: PASS
EXACT MARKET-BAR ANCHORS: PENDING NVT2/NVT5
LOCKED GROUND TRUTH: NO
NCA PRODUCTION MODIFIED: NO
```
