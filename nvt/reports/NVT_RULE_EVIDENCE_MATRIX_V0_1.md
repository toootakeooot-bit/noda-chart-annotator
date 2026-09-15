# NVT Rule Evidence Matrix v0.1 — USDJPY initial corpus

Status: **RESEARCH HYPOTHESES / NOT PRODUCTION RULES**

Corpus: 2026-08-08, 08-22, 08-30, 09-05, 09-12 USDJPY analysis videos.

This matrix separates repeated teacher evidence from one-off observations and maps each hypothesis to the NVT layer that should eventually own it.

| Hypothesis | 08/08 | 08/22 | 08/30 | 09/05 | 09/12 | Evidence strength | Future owner |
|---|---:|---:|---:|---:|---:|---|---|
| Older line/channel may be kept when it still has an active reference role | strong | - | - | strong | - | STRONG (2 independent examples) | NVT7 Lifecycle |
| Newest geometrically valid anchor is not automatically preferred | medium | medium | medium | strong | strong | STRONG | NVT6 Selector + NVT7 |
| Multiple valid candidates can coexist; preference may favor gentler angle | weak | medium | - | medium | explicit strong | STRONG | NVT6 Selector |
| A valid result can be NO-LINE on a timeframe | explicit | - | - | explicit | explicit | STRONG | NVT6 Selector / TF ownership |
| Basic/higher-timeframe structure should be established before advanced lower-TF construction | medium | explicit strong | medium | medium | strong | STRONG | NVT6 hierarchy |
| Wick use is contextual; long/outlier wicks can be noise but wick anchors also matter materially | medium | strong | explicit strong | explicit strong | explicit strong | VERY STRONG | Market Facts + NVT6 |
| Internal movement should be suppressed until a meaningful high/low update changes the recognized wave | strong | strong | explicit strong | strong | explicit strong | VERY STRONG | Market Facts / Turn recognition |
| Lines may be retained for reconstructability/visual memory even when not the sole active structure | explicit strong | - | - | medium | - | MEDIUM-STRONG | NVT7 + Renderer role |
| Teacher line choice depends on which structural scale the line is intended to represent | strong | explicit strong | strong | strong | explicit strong | VERY STRONG | Market Facts + TF ownership + Selector |

## 1. Strongest system-level conclusion

The teacher process is not well described by one rule such as `choose newest two valid TL generations`.

A more faithful future model will likely require three independent decisions:

```text
A. STRUCTURE OWNERSHIP
   Which market wave / timeframe is being represented?

B. CANDIDATE SELECTION
   Among valid anchor pairs for that structure, which line is preferred?

C. LIFECYCLE / DISPLAY ROLE
   Should older lines be active, reference-only, hidden, or retired?
```

The current NCA combines parts of these decisions in a relative Large/Mid classifier plus chronological current/previous lifecycle. NVT must measure each layer separately before changing production.

## 2. Candidate features justified by repeated evidence

Features worth exposing in NVT2/NVT3, without yet assigning weights:

```text
structure/timeframe ownership
anchor pivot kind and confirmation state
high/low update validity
turn span / structural span
cluster membership and right-edge position
slope magnitude (gentleness)
TL and CH contact evidence
closed-bar break state
anchor candle body/wick morphology
wick outlier/noise evidence
relation to higher-timeframe/basic line
relation to previously retained teacher reference
intermediate-pullback coverage
```

## 3. Explicitly rejected shortcuts

Do not assume from the video evidence that:

```text
latest anchor wins
steepest or gentlest always wins
wick must always be used
wick must always be ignored
every timeframe must output TL/CH
previous chronological generation is always the teacher's retained reference
more contacts alone determine the teacher line
```

Each of those shortcuts is contradicted or made conditional by at least one source video.

## 4. Validation consequence

NVT3 comparisons should report at least:

```text
STRUCTURE_SCALE_MATCH
CANDIDATE_PRESENT
ANCHOR_MATCH
SELECTOR_MATCH
NO_LINE_MATCH
LIFECYCLE_ROLE_MATCH
CHANNEL_MATCH
```

A visual mismatch should not be classified as `SELECTION` if the teacher candidate was never generated.

## 5. Current confidence

```text
DATA QUALITY: HIGH
CROSS-VIDEO REPEATABILITY: GOOD
EXACT BAR-LEVEL GROUND TRUTH: PARTIAL / PENDING NVT5
PRODUCTION RULES READY: NO
NVT2 FEATURE-EXPOSURE JUSTIFIED: YES
```
