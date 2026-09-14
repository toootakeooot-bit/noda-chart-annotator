# NCA Normal Run / History Rebuild Audit — 2026-09-14

Status: **SPECIFICATION FIXED / IMPLEMENTATION PENDING**

Repository: `toootakeooot-bit/noda-chart-annotator`  
Branch: `feature/live-draw-baseline-v1`

## 1. Audit purpose

Fix NCA standard operation as **user-initiated Normal Run** and replace the prior automatic closed-bar monitoring trigger with a history-rebuild operating contract.

The top-level `docs/BOUNDARY_V1.md` remains unchanged in authority.

## 2. Before

Prior `docs/DRAWING_OPERATION_V1.md` fixed the following operating model:

```text
new closed bar on each timeframe
 -> automatic monitoring / re-evaluation trigger
 -> local NCA re-evaluation
 -> optional drawing-state update
```

The lifecycle implementation and documentation also treated persisted `current` / `previous` state as the normal progression mechanism between executions.

Operational consequence: if NCA was not run while intervening TL generations occurred, persisted `previous` could represent the previous **NCA-observed** TL rather than the true immediately previous TL generation in market-history reconstruction.

## 3. After

The fixed operating model is now:

```text
USER NORMAL RUN
 -> acquire D1 / H4 / H1 / M15 closed-bar history
 -> rebuild structure chronologically from past to present
 -> determine current / true immediate previous
 -> generate snapshot
 -> validate snapshot
 -> PASS: replace owned NCA_DRAW__ objects
 -> FAIL: keep last valid MT4① drawing unchanged
```

Normal operation explicitly excludes:

- continuous monitoring,
- automatic execution on every newly closed bar,
- periodic polling,
- schedule-based automatic re-evaluation.

## 4. Formal current / previous definitions

`current`:

> Current valid TL generation reconstructed from closed-bar history during the present Normal Run.

`previous`:

> Valid TL generation established immediately before `current`, determined by chronological reconstruction of closed-bar history during the present Normal Run.

Example:

```text
historical sequence:
TL002 -> TL003 -> TL004

final display:
previous = TL003
current  = TL004
```

A previously saved `TL002` must not remain `previous` merely because NCA was not run while `TL003` occurred.

## 5. Display and CH rule

Maximum displayed TL generations remain:

```text
current + immediately previous
```

CH remains subordinate to the parent TL generation. Current and previous TL generations may therefore each carry their corresponding CH.

If history does not establish a valid previous generation, current-only display is valid and previous must not be fabricated.

## 6. Safe replacement rule

The old valid drawing must not be cleared at the beginning of Normal Run.

Fixed sequence:

```text
history acquisition
 -> rebuild
 -> current / previous determination
 -> snapshot generation
 -> validation PASS
 -> replace target NCA_DRAW__ objects
```

On acquisition/rebuild/snapshot/validation failure, keep the last valid drawing unchanged.

Manual objects and every object outside the `NCA_DRAW__` managed identity remain untouched.

## 7. Existing FIXED items preserved

The following remain fixed and unchanged:

- XM MT4① all symbols supported in principle;
- no per-symbol architectural allowlist/hard-code boundary;
- basic timeframes = `D1 / H4 / H1 / M15`;
- production managed prefix = `NCA_DRAW__`;
- NCA local logic (currently Python) owns runtime drawing judgment;
- ChatGPT is not in the runtime judgment path;
- MT4① is the drawing destination;
- TC is not used and is not a dependency;
- NODA Engine remains separate;
- no order/trade execution authority.

## 8. Files changed by this specification fix

- `docs/DRAWING_OPERATION_V1.md`
  - automatic closed-bar trigger superseded;
  - Normal Run fixed;
  - chronological history rebuild required;
  - true current / previous definitions fixed;
  - safe replacement sequence fixed.

- `docs/LIVE_DRAW_LIFECYCLE_V1.md`
  - precedence aligned with Drawing Operation v1;
  - persisted prior-run state made non-authoritative for Normal Run current/previous;
  - chronological reconstruction semantics added;
  - safe replacement boundary added.

- `README.md`
  - active operating description changed from closed-bar automatic monitoring to user Normal Run;
  - legacy continuous/timer material explicitly marked subordinate where conflicting.

## 9. Implementation impact

This task fixes **specification and documentation only**. Existing runtime code is not yet fully compliant.

Known implementation gaps to address separately include:

1. `mt4/NCA_TEST_MarketExporter.mq4`
   - currently timer-driven and USDJPY-specific;
   - must not define Normal Run as periodic polling in production.

2. `tools/run_live_draw_test_usdjpy.py`
   - currently USDJPY-specific;
   - runs each timeframe once over the available input rather than replaying each historical structural transition to reconstruct true generations.

3. `tools/live_draw/lifecycle.py`
   - currently promotes the prior persisted `current` to `previous` when new geometry is selected;
   - does not yet perform a clean Normal Run chronological history rebuild that guarantees the true immediate previous TL.

4. `mt4/NCA_TEST_LiveDraw_Renderer.mq4`
   - currently uses TEST prefix / TEST snapshot assumptions;
   - deletes owned TEST objects before rendering after basic file/header checks;
   - production implementation must use `NCA_DRAW__` and obey rebuild/validate-before-replace semantics.

5. XM all-symbol production path
   - architecture is fixed as all-symbol capable in principle;
   - existing TEST exporter/runner/renderer still contain USDJPY-specific values and require separate implementation work.

## 10. Risk control

No detector semantics, NODA Engine rules, trade execution logic, or TC dependency were introduced by this specification change.

Implementation work must preserve the currently working local NCA drawing logic unless a separate approved work item explicitly changes detector/selection semantics.

## 11. Final fixed state

```text
NCA NORMAL RUN
STATUS: FIXED
TRIGGER: USER NORMAL RUN
MONITORING: NONE
PERIODIC POLLING: NONE
HISTORY REBUILD: REQUIRED
CURRENT: REBUILT FROM CLOSED-BAR HISTORY
PREVIOUS: TRUE IMMEDIATE PREVIOUS TL REBUILT FROM HISTORY
DISPLAY: CURRENT + PREVIOUS
CH: CHILD OF EACH TL GENERATION
PREFIX: NCA_DRAW__
SAFE REPLACE: REBUILD/VALIDATE FIRST, REPLACE AFTER PASS
IMPLEMENTATION: PENDING SEPARATE WORK ITEM
```
