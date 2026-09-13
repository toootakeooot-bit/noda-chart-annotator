# NCA Live Draw v1-A Implementation Audit

Status: **CHATGPT-SIDE IMPLEMENTATION READY / REAL MT4 TEST PENDING**

## Scope implemented

TEST / USDJPY / D1-H4-H1-M15 initial path:

1. MT4 closed-bar OHLC exporter.
2. CSV Market Input reader and validation.
3. Turn Detector v1: 38% retracement, closed-bar close confirmation.
4. Internal TL candidate construction from higher lows / lower highs.
5. CH construction as a parallel subordinate line.
6. TL/CH reaction evidence using direct candle intersection only; no fixed pip/ATR tolerance and no weighted strength score.
7. Provisional relative Large-Dow / Mid-Dow classifier for TEST only.
8. TL Zone from start-anchor wick-to-body width; CH Zone uses the same translated width.
9. Lifecycle state: current + immediately previous generation only.
10. TEST snapshot writer and MT4 renderer.
11. No trade decision fields/actions and no NODA Engine writeback.

## Important provisional details

The following are deliberately not promoted to fixed NODA rules:

- Large/Mid machine classifier version `PROVISIONAL_RELATIVE_STRUCTURE_0.1`.
- R07-style unbroken evidence currently uses post-anchor2 **closed-bar close**, not wick crossing.
- TL/CH reaction evidence currently uses exact line/candle-range intersection, avoiding an invented proximity threshold.
- Turn detector remains version 1.0 PROVISIONAL as fixed in the Baseline.

These are TEST-local detector/selection details and may be revised from real chart observations without changing the fixed Live Draw contract.

## Offline verification

Synthetic deterministic integration test completed successfully on all four TF paths:

- D1: PASS
- H4: PASS
- H1: PASS
- M15: PASS
- Turn detector produced confirmed turns.
- LARGE_DOW and MID_DOW selections were produced on the fixture.
- TL / CH / TL_ZONE_EDGE / CH_ZONE_EDGE snapshot output produced.
- Combined four-TF snapshot: 32 objects + header.
- Re-running identical data is idempotent; no new generation is created.
- Static prohibited-field scan: PASS.

## Not yet verified

The following require the user's TEST MT4 terminal and therefore are not claimed PASS yet:

- MQL4 compile in XM's actual MetaEditor build.
- Real USDJPY# D1/H4/H1/M15 OHLC export.
- Real-data Turn behavior.
- Real-data Large/Mid classifier quality.
- Real-data TL/CH selection quality.
- MT4 visual render alignment and Zone placement.
- Lifecycle behavior across multiple actual 15-minute refresh cycles.

## Safety boundary

This implementation is TEST-only. LIVE is not enabled. Teacher PDF remains Benchmark-only. NODA Engine is untouched.
