# NVT6 Ownership / Candidate Identity Audit — 2026-09-15

Status: **RESEARCH ONLY — PRE-SELECTOR**

Production `tools/live_draw/`, Normal Run, `NCA_DRAW__`, MT4 objects, NODA Engine, trade state: **UNCHANGED**.

## Inputs reviewed

- `NVT6_OWNERSHIP_COMPARISON.json`
- `GT_0003_CANONICAL_CANDIDATE_VIEW.json` schema 0.1
- prior GT_0005 / GT_0006 / GT_0007 Ground Truth and NVT5 replay evidence

## Finding 1 — Candidate presence cannot define ownership

GT_0007 is a timeframe-global H1 NO-LINE negative control but still has many candidate structures, including native P38 and Micro-Dow-derived candidates. Therefore all of the following are insufficient by themselves:

- candidate existence;
- `P38_MICRO` provenance;
- latest confirmed origin bridging.

An ownership gate remains mandatory before selector scoring.

## Finding 2 — GT_0005 and GT_0006 must not be learned as opposite market snapshots

GT_0005 and GT_0006 share the same 2026-09-12 H1 market snapshot. Their gentlest latest-origin `P38_MICRO` candidates are identical. The apparent candidate-count difference comes from expectation/direction filtering, not from different market structure.

Therefore:

- GT_0006 may be used as positive recall evidence for the teacher-discussed H1 falling TL family;
- GT_0005 must remain a structure-specific rejection case until the rejected target structure is explicitly identified;
- do not train a candidate-level ownership rule by treating every GT_0005 H1 candidate as negative.

## Finding 3 — canonical candidate view schema 0.1 was intentionally conservative but over-labeled geometry risk

Schema 0.1 reported:

- source rows: 2696;
- canonical groups: 1773;
- collapsed row excess: 923;
- unsafe groups: 282;
- selected geometry collisions: 0.

However the v0.1 `unsafe` check compared complete anchor dictionaries. That included contextual/confirmation metadata such as bar indices, confirmation indices/times and candle payloads. Those fields can vary without changing the actual TL/CH geometry.

Therefore `unsafe_geometry_group_count=282` must **not** be interpreted as 282 corrupted line geometries.

`build_canonical_candidate_view.py` is revised to schema 0.2 to separate:

- geometry identity;
- context metric variants (`turn_span`, contacts, unbroken state);
- anchor confirmation metadata variants;
- candidate-id-to-multiple-geometry ambiguity.

Selector scoring must occur once per canonical geometry, not once per duplicate source row.

## Finding 4 — selected baseline candidates are not currently implicated

The prior schema 0.1 output reported zero selected geometry collisions. This supports continuing research without treating the current production selection as broken. The identity cleanup is a precondition for experimental NVT6 scoring, not a production hotfix.

## Next research step

Add an evidence-only ownership feature probe using GT_0006 vs GT_0007. Probe, but do not yet turn into hard rules:

- H4 / D1 active-leg relationship at candidate origin and cutoff;
- candidate origin structural role;
- peer-relative gentle-slope rank;
- second-anchor recency rank;
- second-anchor wick strength;
- candidate age / elapsed hours.

Cluster-right-edge requires a separate evidence-driven cluster definition and is not hard-coded in this step.

GT_0005 rejected-target identification remains a parallel required task.

## Gate state

```text
NVT6 CANDIDATE RECALL: PARTIAL PASS
GT_0006 MICRO-DOW RECALL: PASS
GT_0007 NEGATIVE CONTROL: PASS
OWNERSHIP RULE: NOT FIXED
CANONICAL GEOMETRY POLICY: REVISED TO 0.2, RE-RUN REQUIRED
SELECTOR BETA: NOT YET PROMOTED
PRODUCTION WRITEBACK: NONE
```
