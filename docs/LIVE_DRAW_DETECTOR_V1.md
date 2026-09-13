# NCA Live Draw Detector v1

Status: **PROVISIONAL DETECTORS**

These detectors implement the fixed Live Draw contract without modifying NODA Engine rules R01–R20. They are intentionally testable and locally replaceable in TEST.

## 1. Turn Detector v1

### Input

The most recent Small-Dow wave.

### Rule

A Turn is provisionally confirmed when price retraces at least 38% of that wave and a **closed candle close** crosses the 38% retracement level.

#### Rising wave

```text
Low A -> High B
threshold = B - (B - A) * 0.38
closed_bar_close <= threshold
=> TURN_CONFIRMED candidate
```

#### Falling wave

```text
High A -> Low B
threshold = B + (A - B) * 0.38
closed_bar_close >= threshold
=> TURN_CONFIRMED candidate
```

Metadata:

```text
TURN_DETECTOR_VERSION = 1.0
status = PROVISIONAL
confirmation = CLOSED_BAR_CLOSE
retracement = 0.38
```

### Constraints

- Wick-only penetration does not confirm the Turn in v1.
- Unclosed bars do not confirm the Turn.
- This detector is an NCA implementation rule and must not be written back as R01–R03.
- TEST observations may later change the percentage or confirmation method without changing the fixed Live Draw architecture.

## 2. Large-Dow / Mid-Dow classifier v1

The structural classifier must not map timeframe directly to Dow level.

### Large-Dow basis

Use R03/R07-compatible facts:

- spans multiple Small-Dow turns,
- forms a structurally larger movement,
- a Large-Dow TL is basically unbroken at the point it is selected.

The exact machine detector for “structurally larger” remains PROVISIONAL and must be observable in TEST.

### Mid-Dow basis

Treat Mid-Dow as an intermediate structure inside Large-Dow:

- exists inside a larger Large-Dow context,
- contains multiple Small-Dow turns,
- is lower in structural scope than the Large-Dow structure.

A previously broken line alone must **not** classify a structure as Mid-Dow.

### Prohibited shortcut

```text
D1 = LARGE_DOW
H4 = MID_DOW
```

or any equivalent fixed timeframe mapping is prohibited.

## 3. TL generation and in-process selection

TL candidate evaluation is internal to TL generation. Normal Live output must not expose unresolved candidate pools.

### Rising TL geometry

Use two higher lows.

### Falling TL geometry

Use two lower highs.

### In-process selection evidence

Evaluate, as one channel structure:

1. anchor relation,
2. historical/current reaction on the TL side,
3. reaction on the parallel CH side,
4. coherence of TL + CH together.

The selected TL is the only one promoted to Live output.

Existing project selection semantics such as same-role comparison, qualitative reaction evidence, and preference for a gentler slope when otherwise comparable may be used as supporting tie-break semantics, but no new numeric score may be invented.

## 4. CH generator

CH is always subordinate to the selected TL.

- rising TL -> parallel CH on the high side,
- falling TL -> parallel CH on the low side.

CH is evaluated during TL selection because CH-side reactions help determine whether the TL/channel pair is coherent.

## 5. CH-break detector v1

CH may be updated while TL remains fixed.

A wick-only break is insufficient.

Initial provisional re-evaluation evidence is:

```text
body/close-side confirmation
OR
confirmation visible on an upper timeframe
```

After break evidence, CH is moved only after a new outer high/low is structurally confirmed. The replacement CH remains parallel to the parent TL.

The exact definition of “body break” and “upper-timeframe confirmation” remains PROVISIONAL and must be refined from TEST cases.

## 6. Zone detector v1

### TL Zone

Base width is the wick-to-body range of the TL start-anchor candle.

Do not use:

- fixed pip widths,
- ATR widths,
- numeric strength scores.

Outlier-wick exclusion and body extension are deferred for v1 unless already supported by explicit evidence.

### CH Zone

CH Zone width equals TL Zone width and is translated in price to the CH side. Do not independently recalculate CH Zone width.

## 7. Update cadence

All detector promotion decisions use closed bars only.

The initial orchestration cadence is once after each M15 close:

```text
00:01
15:01
30:01
45:01
```

Each cycle may refresh D1 / H4 / H1 / M15 inputs, but a timeframe is structurally updated only when its relevant closed-bar data changed.

## 8. TEST refinement policy

The following may be changed by focused TEST work without changing the fixed baseline contract:

- Turn retracement percentage,
- Turn close/body confirmation details,
- Large-Dow / Mid-Dow machine-classification details,
- CH-break body/upper-timeframe confirmation details.

Every detector revision should carry a version and retain enough audit data to compare before/after behavior.
