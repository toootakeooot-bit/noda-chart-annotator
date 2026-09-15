# NVT Materials Checklist v1

Status: **FIXED FOR NVT v1 INTAKE**  
Fixed date: 2026-09-15

## 1. Minimum materials required per reference case

For each still image or video segment, collect as much of the following as is available:

```text
source_id
source_type: IMAGE | VIDEO
original file or external storage location
symbol
timeframe
approximate chart date range
teacher decision time / video timestamp
whether the chart is live or historical replay
visible teacher drawings
any teacher-spoken explanation linked to the drawing
```

If symbol/timeframe/date cannot be established, the case may still be stored as DRAFT but cannot become a hard regression case.

## 2. Still-image materials

Preferred:

- original-resolution screenshot, not a compressed social-media thumbnail;
- whole chart including time axis and price axis;
- symbol/timeframe visible;
- enough history visible to identify anchor bars;
- if available, a second screenshot immediately before/after the drawing change.

Useful but optional:

- marked-up copy identifying which lines are teacher-drawn;
- notes describing color/width conventions.

## 3. Video materials

Preferred:

- original video file or stable local/Drive reference;
- uncut segment around the drawing event;
- visible time axis / timeframe / symbol when possible;
- audio retained if the teacher explains why a line is added/kept/moved/deleted;
- timestamp of important events if already known.

For lifecycle analysis, the strongest videos show the chart before and after a drawing change, not only the finished chart.

## 4. Market-data materials

For time-frozen replay, NVT needs historical OHLC covering the reference period.

Preferred source:

- the same XM MT4 symbol where practical;
- D1/H4/H1/M15 closed bars consistent with current NCA input format;
- sufficient history before the teacher decision to reconstruct candidate structures.

If the teacher chart comes from a different broker/data feed, record that fact because small high/low differences can move anchors.

## 5. Teacher-rule source material

If available, provide supporting source material that explains drawing definitions, such as:

- course PDFs/slides;
- screenshots with annotations;
- written notes/transcripts;
- specific video chapters where line-selection or retention rules are explained.

These are supporting evidence. Observed chart behavior and explicitly stated teacher rules must be kept distinguishable.

## 6. Recommended starter dataset

NVT1 can start with a small but varied set rather than waiting for a large archive.

Recommended first intake:

```text
Still images: 5-10 usable cases
Videos:      2-3 segments containing actual drawing changes
Timeframes:  include at least D1 plus one lower timeframe
Regimes:     trend / reversal or transition / range-like structure if available
```

The current two comparison screenshots can be registered as initial DRAFT evidence once source identity, symbol, timeframe, and approximate decision date are confirmed.

## 7. Material quality grading

Each source should receive one of:

```text
A = original / high resolution, axes and context sufficient
B = usable but one important field is approximate
C = visual reference only; insufficient for hard anchor regression
```

Only A/B material should normally become LOCKED Ground Truth.

## 8. Storage policy

Large source image/video files should remain outside GitHub by default.

GitHub stores:

- manifests;
- Ground Truth JSON;
- event timestamps;
- candidate dumps;
- reports;
- audit records.

Source media can stay on local storage or Google Drive and be referenced by stable `source_id` / external path description.

## 9. What is needed next for NVT1

Immediate intake needed from the user:

1. identify the source of the current Noda-sensei screenshot(s);
2. confirm symbol/timeframe for each;
3. give approximate chart/decision date if known;
4. provide the first original video or a representative segment containing line drawing/change behavior;
5. if available, provide any Noda reference material that explicitly explains why those lines are selected or kept.

Exact anchor labeling can be done during NVT1; it does not need to be prepared manually in advance.
