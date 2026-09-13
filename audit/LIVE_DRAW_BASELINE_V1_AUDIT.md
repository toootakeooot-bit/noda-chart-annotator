# NCA Live Draw Baseline v1 Audit

## Decision

```text
NCA LIVE DRAW BASELINE V1
STATUS: FIXED
```

The repository contract has been changed from a Teacher-PDF-primary purpose to a Live-Draw-primary purpose while preserving the existing Teacher/PDF path as Teacher Benchmark / Regression.

This work intentionally does **not** implement the full Live Market Pipeline yet.

## 1. Files added

- `docs/LIVE_DRAW_BASELINE_V1.md`
- `docs/LIVE_DRAW_LIFECYCLE_V1.md`
- `docs/LIVE_DRAW_DETECTOR_V1.md`
- `audit/LIVE_DRAW_BASELINE_V1_AUDIT.md`

## 2. Existing files migrated

### `README.md`

Previous state: repository purpose explicitly said “reproduce Teacher-drawn chart geometry from the weekly chart PDF”.

Action: **migrated to new Baseline**.

Current role: Live Draw is the primary purpose; Teacher/PDF is benchmark/regression.

### `spec/PDF_ONLY_POLICY.md`

Previous state: Teacher PDF / chart image listed as active primary source.

Action: **moved to Teacher Benchmark scope**.

Current role: Teacher evidence and weekly chart handling remain available, but missing Teacher material cannot stop Live Draw.

### `spec/PDF_GEOMETRY_POLICY.md`

Previous state: PDF geometry policy described the active geometry path.

Action: **moved to Teacher Benchmark scope**.

Current role: deterministic PDF geometry remains available for benchmark/regression and must not overwrite or gate Live Draw.

### `PHASE6J_AUDIT.md`

Action: **maintain as historical audit evidence**.

It documents the earlier PDF-geometry phase and is not rewritten because it is a historical phase record.

### `tools/local_pdf_teacher_parser.py`
### `tools/pdf_geometry_extractor.py`
### `tools/pdf_geometry_extractor_compat.py`
### `tools/run_pdf_only_once.py`
### `run_pdf_only_once.cmd`
### PDF-related setup scripts

Action: **maintain, benchmark-only**.

No deletion is required. Their presence does not conflict with Live Draw as long as they remain outside the required Market Pipeline and do not control Live lifecycle state.

### `spec/noda_rules_current.json`

Action: **maintain**.

No R01–R20 content was modified by this Baseline work. The new 38% Turn detector, lifecycle timing, and exact machine-classification details are NCA implementation semantics, not new NODA Engine rules.

Existing selection semantics that retain multiple Anchor/TL candidates are compatible with the new Baseline only as **internal selection evidence**. Live output publishes only the selected TL.

## 3. Conflict audit

| Area | Previous state | New state | Resolution |
|---|---|---|---|
| Primary purpose | Teacher PDF reproduction | MT4 OHLC Live Draw | migrated |
| Teacher PDF gate | active/primary | benchmark only | migrated |
| Missing Teacher week | ends PDF path | must not stop Live | fixed |
| NODA rules R01–R20 | project rule source | unchanged | maintain |
| Candidate handling | multiple candidates retained | internal comparison allowed; selected TL only published | compatible with clarification |
| Turn exact detector | not fixed | 38% closed-bar detector v1 | provisional NCA detector |
| R18 update timing | TBD | NCA lifecycle fixed for Live Draw | NCA implementation only; no R18 rewrite |
| Timeframe mapping | no fixed mapping | explicitly prohibited | maintain/strengthen |
| Trade fields | prohibited | prohibited | maintain |
| PDF geometry code | active main path | Teacher Benchmark | reclassified |
| Market OHLC Live path | absent in repository | required next implementation | open next work |

## 4. Fixed contract verification

- [x] TEST / LIVE responsibilities fixed.
- [x] Initial 3 canonical symbols fixed: USDJPY / GOLD / US100.
- [x] D1 / H4 / H1 / M15 fixed as observed timeframes.
- [x] Large-Dow / Mid-Dow only as Live output structural levels.
- [x] TL primary; CH / TL Zone / CH Zone subordinate.
- [x] Turn Detector v1 documented.
- [x] TL selection occurs inside TL generation.
- [x] TL-side and CH-side reactions both participate in TL selection.
- [x] `Break != redraw` fixed.
- [x] New TL waits for new Turn / new high-low confirmation.
- [x] Old TL deletion is separate from new TL creation.
- [x] Cross-structure retention allowed.
- [x] Maximum visible generations fixed to current + previous.
- [x] Closed bars only.
- [x] Market Pipeline and Teacher Pipeline separated by contract.
- [x] Teacher PDF agreement removed from Live Draw pass gates.
- [x] NODA Engine boundary preserved.
- [x] Entry / SL / TP / RR / Lot / Long-Short / Order / Ticket remain prohibited.
- [x] Existing repository purpose conflict resolved in README/PDF policy docs.

## 5. Provisional items intentionally left open

The following are not Baseline blockers and remain local TEST refinement points:

1. Turn detector details beyond v1 (`38%`, closed-bar close).
2. Exact machine detector for Large-Dow vs Mid-Dow.
3. Exact definition of CH body-break / upper-timeframe confirmation.
4. Advanced Zone outlier-wick exclusion/body-extension behavior.
5. Exact qualitative reaction implementation used inside TL selection.

Changes to these items must remain versioned and must not silently change the FIXED CONTRACT.

## 6. Items not implemented in this work

The following do not yet exist as the new production code path in this repository and must be implemented in the next work:

- MT4 OHLC Market Input adapter for the 3 canonical symbols.
- D1/H4/H1/M15 closed-bar refresh orchestration.
- Turn Detector v1 executable implementation.
- Large-Dow / Mid-Dow executable classifier.
- TL selection/generation implementation.
- CH generation and CH-only update implementation.
- TL/CH Zone generation.
- two-generation lifecycle state store.
- Live Snapshot schema/output.
- TEST renderer integration for the new Live objects.
- LIVE promotion gate.

This is intentional because the request required Baseline fixation before large Live implementation.

## 7. Next work recommendation

Proceed with a narrow first implementation:

```text
NCA Live Draw v1-A
Market Input + Turn Detector + one-symbol TEST path
```

Recommended first target:

```text
TEST
USDJPY
D1 / H4 / H1 / M15
closed bars only
```

The first implementation should stop before LIVE promotion and should emit auditable intermediate facts for Turn, structural classification, selected TL, CH, and Zone.

## 8. Final audit result

No Baseline-blocking conflict remains in the repository documentation/specification layer.

The repository still lacks the new executable Market Pipeline, but that is a **next implementation gap**, not a Baseline conflict.

```text
NCA LIVE DRAW BASELINE V1
STATUS: FIXED
NEXT: LIVE DRAW v1-A IMPLEMENTATION
```
