# NVT5 Video-Frame Review — USDJPY — 2026-09-15

Status: AUDIT REVIEW COMPLETE / GROUND TRUTH NOT YET LOCKED

## Scope

Reviewed the NVT5 review bundle together with Teacher video frames for GT_0001, GT_0002, GT_0003, GT_0004, GT_0005, GT_0006, and GT_0007.

This audit does **not** modify Ground Truth, the production selector, `tools/live_draw/`, Normal Run, MT4 objects, or trade state.

## Confirmed NVT5 integrity

- Review bundle status: PASS.
- 7 workbenches present; no missing or duplicate cases.
- 5 replay manifests present.
- All 5 `look_ahead_guard` checks PASS.
- Exact cutoffs were derived from actual XM closed-bar history.

## Important new finding: several mismatches appear to be Candidate/Structure-scale issues, not only Selector issues

### GT_0005 and GT_0007 — H1 NO-LINE

Teacher explicitly expects no H1 line. Baseline NCA still selects Large/Mid falling candidates. These remain confirmed Structure Ownership / NO-LINE mismatches.

### GT_0006 — H1 descending mid TL

Teacher video frames show a short, early-September H1 structure: the starting technical high is around September 1-3 and the compared cluster-edge highs extend through roughly September 10/11. Teacher explicitly compares multiple later cluster-edge candidates and prefers a gentler valid line.

However, the current NVT5 workbench's `RECENT_ANCHOR2` candidates top out at `2026-09-02T04:00:00`; the baseline selected lines start in June and end on September 2. This is materially different from the visible Teacher structure.

Therefore GT_0006 must **not** be classified as a pure Selector problem yet. First determine whether the full Candidate Pool contains any falling candidate with anchor1 in the September 1-3 window and anchor2 in the September 4-11 window. If none exists, the primary fault is Candidate generation / Turn recognition / Structure ownership.

### GT_0001 — D1 secondary rising TL

Teacher video visually constructs the rising channel from the major April 2025 low into a later 2025 low cluster. The current baseline-selected D1 candidates in the workbench instead use very long structures such as 2018/2020 -> 2026.

This is a strong scale discrepancy. Full-pool probing is required before calling it a Selector mismatch.

### GT_0004 — D1 original rising reference

Teacher video shows the persistent original D1 rising reference as part of the 2025-origin rising channel family. The intended monitoring reference is explicitly preferred over a newer PC re-anchoring.

The workbench baseline Large candidate is `2018-12-04 -> 2026-08-03`, which is visibly a different structural scale from the Teacher reference shown in the video. This is likely a Candidate/Structure-scale issue plus a Lifecycle persistence issue. Both responsibilities must remain separate.

### GT_0003 — H4 wick-to-wick rising TL

Teacher video reviews a 2026 H4 rising support/channel line, approximately tied to the February 2026 low and the late-April/early-May 2026 low, while questioning whether a long wick should be treated as noise.

The current workbench baseline lines originate in 2025 and terminate around August 2026. Again, the visible Teacher line and baseline selected geometry are on different structural scales. Full-pool probing is required.

### GT_0002 — initial CH retained + updated CH current

The NVT5 workbench gives `TEACHER_D1_CH_INITIAL` and `TEACHER_D1_CH_UPDATED` the same candidate shortlist and the same single `ch_anchor` per candidate view. Therefore the current workbench cannot adjudicate the key Teacher evidence: two CH roles can coexist, with one retained as REFERENCE and one updated as CURRENT.

GT_0002 remains primarily a Lifecycle evidence case. Geometry probing should only verify whether multiple CH geometries exist for the Teacher-like parent TL; it must not collapse REFERENCE/CURRENT into simple chronology.

## Action added

Created `nvt/cases/NVT5_VISUAL_ANCHOR_HYPOTHESES_20260915.json` containing broad video-derived date windows, explicitly marked as review hypotheses rather than Ground Truth.

Created `tools/nvt/probe_teacher_anchor_windows.py` and `setup/RUN_NVT5_TEACHER_ANCHOR_PROBE.cmd`.

The probe searches the **full exact time-frozen Candidate Pools**, not only the shortlist, and reports:

- `PRESENT_WITHIN_WINDOWS` vs `ABSENT_WITHIN_WINDOWS` for TL cases,
- latest anchor1/anchor2 times available in the direction,
- exact window-match candidates,
- nearest misses when no exact window match exists,
- parent geometry and distinct CH anchors for GT_0002,
- NO-LINE cases without attempting Teacher-match geometry.

## Gate before NVT6

Do not modify the Selector yet.

First run the Teacher Anchor Window Probe and classify each remaining Teacher-line case as:

1. Candidate present at the Teacher structural scale -> Selector/Lifecycle investigation may proceed.
2. Candidate absent at the Teacher structural scale -> fix or model Candidate generation / Turn / Structure ownership first.
3. Geometry present but role differs -> Lifecycle problem.

This classification is required before NVT6 implementation.
