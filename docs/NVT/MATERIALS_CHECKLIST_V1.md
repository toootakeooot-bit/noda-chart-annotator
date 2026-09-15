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

For the initial NVT corpus, still images are secondary evidence. Prefer extracting evidence frames from the primary video source so the still frame remains traceable to a video timestamp and surrounding drawing event.

## 3. Video materials

Preferred:

- original video file or stable local/Drive reference;
- uncut segment around the drawing event;
- visible time axis / timeframe / symbol when possible;
- audio retained if the teacher explains why a line is added/kept/moved/deleted;
- timestamp of important events if already known.

For lifecycle analysis, the strongest videos show the chart before and after a drawing change, not only the finished chart.

For the initial NVT corpus, video is the primary evidence source. Static Ground Truth cases may be created by extracting representative frames from the video, but the original video/timestamp remains the authoritative source reference.

## 4. Initial corpus scope — FIXED

Initial NVT analysis is centered on **USDJPY**.

Primary collection window:

```text
2026-08-06 through 2026-09-15
approximately the most recent 40 days
```

This 40-day window is the preferred first corpus for NVT1-NVT4. The purpose is to keep market context, teacher behavior, and replay data relatively coherent while collecting enough examples of drawing changes.

The initial corpus should prioritize USDJPY videos that contain one or more of:

- a new TL/CH being added;
- an existing line being retained despite a newer local structure;
- a line being moved/redrawn;
- a line being removed/retired;
- a major/long-lived structure remaining while a shorter-term structure changes;
- spoken explanation of why a line is selected or retained.

Material outside this 40-day window is not prohibited, but should normally be added after the initial USDJPY corpus is established or when it provides a uniquely useful rule example.

## 5. Market-data materials

For time-frozen replay, NVT needs historical OHLC covering the reference period.

Preferred source:

- the same XM MT4 symbol where practical;
- D1/H4/H1/M15 closed bars consistent with current NCA input format;
- sufficient history before the teacher decision to reconstruct candidate structures.

If the teacher chart comes from a different broker/data feed, record that fact because small high/low differences can move anchors.

## 6. Teacher-rule source material

If available, provide supporting source material that explains drawing definitions, such as:

- course PDFs/slides;
- screenshots with annotations;
- written notes/transcripts;
- specific video chapters where line-selection or retention rules are explained.

These are supporting evidence. Observed chart behavior and explicitly stated teacher rules must be kept distinguishishable.

## 7. Recommended starter dataset

NVT1 can start with a small but varied set rather than waiting for a large archive.

Recommended first intake within the USDJPY 40-day window:

```text
Primary videos:        3-5 useful source videos or segments
Evidence frames:       5-10 extracted static cases
Timeframes:            include D1 plus at least one of H4/H1/M15 where visible
Drawing-event classes: ADD / KEEP / MOVE-REDRAW / DELETE-RETIRE where available
Regimes:               trend / transition-reversal / range-like structure if available
```

The current comparison screenshots can be registered as initial DRAFT evidence if their source-video timestamp and approximate chart/decision date can be linked.

## 8. Material quality grading

Each source should receive one of:

```text
A = original / high resolution, axes and context sufficient
B = usable but one important field is approximate
C = visual reference only; insufficient for hard anchor regression
```

Only A/B material should normally become LOCKED Ground Truth.

Video-derived stills should retain their source-video ID and timestamp so the before/after context can be recovered.

## 9. Storage policy

Large source image/video files should remain outside GitHub by default.

GitHub stores:

- manifests;
- Ground Truth JSON;
- event timestamps;
- candidate dumps;
- reports;
- audit records.

Source media can stay on local storage or Google Drive and be referenced by stable `source_id` / external path description.

## 10. What is needed next for NVT1

Immediate intake needed from the user:

1. provide the first USDJPY source video from the preferred 40-day window, or a representative segment;
2. identify the approximate recording/posting date if known;
3. leave audio intact when the teacher explains drawing logic;
4. if a useful frame has already been extracted, keep or provide the video timestamp linking it back to the source video;
5. if available, provide any Noda reference material that explicitly explains why those lines are selected or kept.

Exact anchor labeling and static-frame extraction can be done during NVT1; they do not need to be prepared manually in advance.
