# NVT8-H USDJPY User Adjudication — 2026-09-16

Status: **RECORDED / USER OPERATIONAL EVIDENCE / RESEARCH ONLY**

This audit records the user's adjudication of the three flagged USDJPY historical cases from `NVT8H_USDJPY_REVIEW_BUNDLE.json` after ChatGPT-first review.

Important boundary:
- This is **not** teacher Ground Truth.
- This is **not** strict source-level NVT8 held-out validation.
- This does **not** retroactively modify the frozen NVT7 scoped beta.
- Production Normal Run / `tools/live_draw` / `NCA_DRAW__` remain unchanged.

## HIST_03 — 2026-06-19 H1

User interpretation:
- Green lines are the active TL/CH.
- Price briefly broke below the TL.
- However, the lows did **not** make a meaningful lower-low update.
- Therefore the structure should **not** yet be classified as descending.
- Do **not** draw a main H1 descending TL.
- A smaller-Dow BR line may optionally be drawn (pink example), but it must not promote the parent H1 structure to downtrend.

Research implication:
1. `TL_BREAK != DIRECTION_FLIP`.
2. Direction transition requires market-structure confirmation, especially a meaningful low update.
3. Optional internal/small-Dow lines must remain subordinate to parent structure ownership.

## HIST_07 — 2026-07-24 H1

User interpretation:
- After the green HIST_03 TL is broken, a cyan redraw may be made.
- Once another valid line arrives, the old green line may be retired.
- However, because the green line is gentler, the steeper cyan line may instead be the one removed.
- A later yellow redraw can capture the structure more broadly; in that situation, retire green.
- The yellow line later acted as a boundary, supporting the broader-structure interpretation.

Research implication:
1. Reference retention is **conditional**, not permanent.
2. Lifecycle replacement is not `newest wins`.
3. A gentler line with broader structural ownership can survive a steeper interim redraw.
4. A later line that structurally subsumes the old line can legitimately retire the old reference.
5. This is the first explicit **user operational evidence** for RETIRE/DELETE semantics, but not teacher evidence.

## HIST_08 — 2026-07-31

User interpretation:
- Keep the prior lines at this moment.
- H1 and H4 TLs have both been broken.
- Primary judgment should now move to the D1 TL.
- A new H1 descending TL is not required for the primary decision at this point.

Research implication:
1. Broken lower-timeframe lines can remain visible as references.
2. Visibility/lifecycle and **decision ownership** are separate dimensions.
3. After H1/H4 structural breaks, decision ownership can escalate to the parent D1 structure.
4. This suggests a research-only ownership state such as `DEFER_TO_PARENT_TF`, but no state is added to the frozen beta during this batch.

## Aggregate interpretation

The three adjudications add three important post-freeze findings:

- **Direction confirmation:** a TL break alone is not sufficient; structural high/low updates matter.
- **Conditional retirement:** old references may eventually be removed when a broader/gentler replacement better captures the structure.
- **Timeframe ownership escalation:** after lower-TF line breaks, the relevant decision layer may move upward rather than immediately drawing a new opposite lower-TF line.

These findings should be implemented only in a **new research candidate after this batch**, followed by a separate regression. The original NVT7 scoped beta remains frozen for auditability.

Source record: `nvt/adjudication/NVT8H_USDJPY_USER_ADJUDICATION_BATCH01.json`
