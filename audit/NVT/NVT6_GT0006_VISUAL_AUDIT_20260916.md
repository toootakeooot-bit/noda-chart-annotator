# NVT6 GT_0006 Visual Audit — 2026-09-16

Status: **RESEARCH ONLY / VISUAL GEOMETRY NARROWED / EXACT ANCHOR NOT LOCKED**

## 1. Inputs

- Ground Truth case: `GT_0006`
- Source video: `分析共有_26-9-12.mp4`
- Teacher interval: `00:30:50-00:31:49`
- Ownership Gate C survivors: 13
- Current cross-feature research lead: anchor1 `2026-09-02 04:00 / 160.387` -> anchor2 `2026-09-11 15:00 / 154.480`

## 2. Direct video observations

The teacher sequence is not a single ranking step.

1. `00:30:50+`: identify the true technical high / origin.
2. `~00:31:00`: identify several structurally valid cluster-right-edge alternatives.
3. `00:31:08+`: a later raised high may be used to redraw the line.
4. `00:31:14+`: teacher explicitly prefers a gentler angle because it exposes intermediate pullbacks and break-and-return structure.
5. `00:31:42+`: an unusually long wick may be treated as noise contextually.

Therefore the selector model should preserve this order rather than collapsing all evidence into one flat score.

## 3. Independent MT4 geometry sample from the video

Around `00:31:12`, the selected object tooltip visibly shows:

- object: `Trendline 55257`
- line value: approximately `159.560`

At the same cursor position, the MT4 status bar shows:

- time: `2026.09.03 11:00`
- O `157.042`
- H `157.137`
- L `156.525`
- C `156.692`
- V `7914`

This gives one independent line-geometry sample that can be compared against the NVT6 candidate family.

## 4. Candidate comparison

Using common NVT6 anchor1:

- `2026-09-02 04:00 / 160.387`

and the candidate slope, project each candidate to `2026-09-03 11:00`.

The closest candidates are:

| anchor2 | price | projected value | error vs 159.560 |
|---|---:|---:|---:|
| 2026-09-11 11:00 | 154.367 | 159.550139 | 0.009861 |
| 2026-09-11 02:00 | 154.609 | 159.550000 | 0.010000 |
| 2026-09-11 15:00 | 154.480 | 159.580317 | 0.020317 |

The next candidate (`2026-09-10 04:00 / 153.737`) is already about `0.2467` away at the same sample time.

So the video geometry reduces the 13 Gate-C survivors to a three-candidate gentle family. The current `09-11 15:00` research lead remains inside that family, but the video sample alone does **not** distinguish it reliably from `09-11 02:00` or `09-11 11:00`.

## 5. Audit conclusion

### Confirmed

- GT_0006 is a positive H1 line-selection case.
- Gate C still behaves as useful research evidence.
- Teacher reasoning is sequential: ownership -> structurally valid cluster alternatives -> optional later-high re-anchor -> gentle-angle preference -> wick-noise context.
- The unique cross-feature research lead is geometrically plausible and survives direct video comparison.
- Most of the original 13 candidates are inconsistent with the sampled teacher line geometry.

### Not confirmed

- Exact teacher anchor2 bar among `2026-09-11 02:00`, `11:00`, `15:00`.
- Hard selector winner.
- Production rule.

### Required before hard anchor lock

One of the following is still required:

1. exact MT4 object parameter coordinates from the source video/object, or
2. a second independent tooltip/time geometry sample on the same teacher trendline, or
3. a visually unambiguous bar-level anchor match against the frozen OHLC replay.

## 6. Selector-beta correction

Do **not** model GT_0006 as one flat `cluster_right_edge + gentle + recency` score.

Research order should be:

`STRUCTURE/OWNERSHIP -> CLUSTER-RIGHT-EDGE VALID ALTERNATIVES -> OPTIONAL LATER-HIGH REANCHOR -> GENTLE-ANGLE PREFERENCE -> WICK-NOISE TAG`

This preserves the teacher's actual explanation order and avoids accidentally treating the final gentlest/latest point as if it were the initial cluster-right-edge definition.

## 7. Safety / production impact

- Production Normal Run modified: **NO**
- Production `turn_detector.py` modified: **NO**
- `NCA_DRAW__` modified: **NO**
- MT4 production objects written: **NO**
- Trade authority: **NONE**
