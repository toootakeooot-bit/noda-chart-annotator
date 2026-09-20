# NVT9 Four-Week Validation Protocol

Audit ID: ID10IQ200  
Baseline: 2026-09-19 approved visual state  
Frozen baseline branch: `baseline/nvt9-0919-approved`  
Frozen baseline commit: `436a17a74919353351675921c11e3bf080ea07a3`

## Cases

Use four weekly labels. Each replay uses only MT4 bars strictly earlier than Saturday 00:00 in the MT4 export time basis.

- 2026-08-22
- 2026-08-29
- 2026-09-05
- 2026-09-12

This intentionally resolves each case to the last available Friday market bar and prevents future leakage.

## Frozen rules during this pass

Do not modify geometry rules after viewing only one historical case. Complete all four cases first.

Frozen for the first pass:

- 38% = Turn/Pivot reaction confirmation; not an HL price.
- FALLING candidate = HIGH1 -> LOW(HL) -> HIGH2, HIGH2 < HIGH1.
- RISING candidate = LOW1 -> HIGH(HL) -> LOW2, LOW2 > LOW1.
- Current research activation = closed-bar close through the decision HL.
- HL stays visible after break and has the source-TF TL color.
- Plan B = source TF displayed on itself + one higher chart.
- Current only / nearest family only / no far-context family.

## Comparison order

For each weekly case:

1. Compare static geometry against an exact-date PDF/chart if one exists.
2. Compare video to resolve lifecycle/timing:
   - when the pivot became confirmed;
   - when the HL became actionable;
   - whether break semantics should be wick or close;
   - whether a later continuation should replace or preserve the active TL.
3. Record mismatches without changing the rule immediately.

## Record per timeframe

For D1, H4, H1, M15 record:

- TL direction.
- TL anchor1 time/price.
- TL anchor2 time/price.
- Decision HL time/price.
- Whether the teacher/source has the same TL.
- Missing line.
- Extra line.
- Same line but wrong anchor.
- Same anchors but wrong activation time.
- Display-map mismatch.
- Evidence source: PDF page or video timestamp.

## Change-control rule

After all four cases are reviewed, group mismatches by one root cause. Apply one rule change at a time and regression-check:

1. all four historical cases; and
2. the frozen 2026-09-19 baseline.

A change that fixes one older week but breaks the 2026-09-19 baseline is not accepted automatically.
