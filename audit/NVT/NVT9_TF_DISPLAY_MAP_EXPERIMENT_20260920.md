# NVT9 09/19 Timeframe Display Mapping Experiment

Audit ID: ID10IQ200  
Date: 2026-09-20  
Status: RESEARCH PREVIEW IMPLEMENTED / PRODUCTION UNCHANGED

## User visual observation

The current MT4 screenshots support a display interpretation different from the earlier cross-TF ownership interpretation:

- on the H4 chart, the aqua structural lines were D1-derived;
- on the M15 chart, the aqua structural lines were H1-derived;
- independent M15 structural lines were not part of the original intended display.

The working display hypothesis is therefore:

- D1 structure -> display on H4
- H4 structure -> display on H1
- H1 structure -> display on M15
- M15 structure -> no independent structural-line display

## Important semantic correction

This experiment does NOT mean:

- H4 structure becomes D1-owned;
- H1 structure becomes H4-owned;
- M15 structure becomes H1-owned.

Instead:

- structural_owner_tf remains equal to source_tf;
- display_tf is one step lower;
- the display layer is separated from structural ownership.

This avoids converting a chart-presentation convention into a market-structure ownership rule.

## Research implementation

A dedicated policy manifest and builder create an audit-only snapshot from the deep lifecycle state.

The snapshot preserves:

- LARGE_DOW and MID_DOW;
- CURRENT and PREVIOUS;
- TL, CH, TL_ZONE_EDGE, CH_ZONE_EDGE.

The CSV `timeframe` field is intentionally the display timeframe for the isolated research renderer.

Expected rows when all deep lifecycle slots exist:

- H4 receives 16 rows from D1;
- H1 receives 16 rows from H4;
- M15 receives 16 rows from H1;
- 16 M15-source rows are intentionally omitted.

## Isolated renderer

`mt4/NCA_NVT9_TFMap_Preview_Renderer.mq4`

Ownership prefix:

`NVT9_TFMAP__`

The renderer does not own or delete:

- Production `NCA_DRAW__`;
- manual MT4 objects;
- trade objects.

It is one-shot and has no timer or trading functions.

## Local runner

Use:

`setup\RUN_NVT9_TF_MAP_PREVIEW_0919.cmd`

This rebuilds the deep lifecycle state and produces:

- `NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv`
- `NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json`

## Gate interpretation

This is a visual experiment, not a Production promotion.

The next evidence step is an MT4 visual comparison on H4, H1 and M15.

If the mapped preview reproduces the intended historical aqua-line layout better than same-timeframe rendering, the display-timeframe layer should be promoted into NVT9 design while keeping structural ownership unchanged.


## 2026-09-20 display-density refinement

User clarified that the display objective is not to show every structurally valid line.

Primary display objective:

- make the structures nearest current price easy to identify;
- omit far redundant lines;
- retain a farther line when it is useful to make the broader direction understandable.

The research display source set is now:

- D1 chart: D1
- H4 chart: D1 + H4
- H1 chart: H4 + H1
- M15 chart: H1 + M15

H1/H4 are allowed to represent one merged structural family when broad turns, long adjustments, or long ranges make the two scales non-separable. Exact geometry duplicates may be deduplicated automatically; non-exact H1/H4 merging is not automatic.

### Price relevance

Selection is performed at the structural-family level rather than on individual line objects.

For each family, TL and CH are projected to the latest closed bar of the display timeframe.

Distance to current price is:

- zero when current price is inside the TL/CH channel;
- otherwise the distance to the nearest projected channel boundary.

No fixed pip threshold and no ATR threshold are used.

The preview keeps the nearest two families as the near-price set. They retain TL, CH and zone edges.

If the near-price set does not contain higher-timeframe context, or its directions conflict, at most one farther CURRENT higher-timeframe family may be retained as directional context. That far context renders TL + CH only, without zone edges.

The count of two near families and one context family is a research-preview control, not a frozen Production rule.


## Plan B direction correction

A prior implementation inverted the user's instruction.

Incorrect interpretation that must not be reused:

- H4 chart <- D1 + H4
- H1 chart <- H4 + H1
- M15 chart <- H1 + M15

The user's intended Plan B is source-oriented:

- H4 structure -> H4 chart AND D1 chart
- H1 structure -> H1 chart AND H4 chart
- M15 structure -> M15 chart AND H1 chart
- D1 structure -> D1 chart

Equivalent chart-oriented view:

- D1 chart = D1 + H4 structures
- H4 chart = H4 + H1 structures
- H1 chart = H1 + M15 structures
- M15 chart = M15 structures

This is now locked by the manifest and self-test. The phrase "source -> self + one higher chart" is the canonical direction.

The current-price relevance filter still applies inside each chart's assigned source set.
