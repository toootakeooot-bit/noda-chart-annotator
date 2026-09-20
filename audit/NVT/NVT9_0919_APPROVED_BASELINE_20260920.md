# NVT9 2026-09-19 Approved Visual Baseline

Audit ID: ID10IQ200  
Approved in chat: 2026-09-20  
Baseline branch: `baseline/nvt9-0919-approved`  
Baseline commit: `436a17a74919353351675921c11e3bf080ea07a3`

## User-approved state

The 2026-09-19 USDJPY four-timeframe preview was accepted as the current visual baseline.

Frozen behaviors:

- Turn/Pivot reaction confirmation remains 38%.
- 38% is not an HL price.
- FALLING TL: HIGH1 -> LOW(decision HL) -> HIGH2, with HIGH2 < HIGH1.
- RISING TL: LOW1 -> HIGH(decision HL) -> LOW2, with LOW2 > LOW1.
- A new-direction TL is eligible only after the decision HL is crossed.
- Current research crossing implementation is closed-bar close; this remains provisional pending video/PDF comparison.
- Decision HL remains visible after the break and uses the source-timeframe TL color.
- Plan B display mapping is source -> self + one higher chart:
  - H4 -> H4 + D1
  - H1 -> H1 + H4
  - M15 -> M15 + H1
- Destination charts do not reselect source geometry.
- Audit preview is clean-chart / drawing-only.

## Historical validation next

Replay the four Saturdays immediately before 2026-09-19:

- 2026-08-22
- 2026-08-29
- 2026-09-05
- 2026-09-12

For each case, use only bars strictly earlier than the case date at 00:00 in the exported MT4 time basis. This makes the effective market cutoff the last available Friday bar and prevents future leakage.

Do not change the approved geometry rules while replaying the four historical cases. Record mismatches first. Only after all four are reviewed should a rule change be proposed.

## Source comparison order

1. Static PDF/chart evidence when an exact matching date/time exists.
2. Video evidence to resolve lifecycle questions such as when the TL/HL became eligible, whether a break is wick-based or close-based, and whether a later continuation should replace the line.
3. Any rule change must cite the historical case that requires it and must be regression-checked against the 2026-09-19 approved baseline.
