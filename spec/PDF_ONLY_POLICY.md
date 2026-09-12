# PDF-only Source Policy v0.5

## Decision
Effective immediately, NODA Chart Annotator proceeds with the information already available. Weekly video is not part of the active pipeline. Teacher rationale mining from old videos is deferred and may be added later as an enrichment layer.

## Active sources
1. Teacher chart PDF / chart image.
2. Chatwork `分析共有` post metadata and links.
3. NODA rules R01–R20 currently fixed by the project.
4. Confirmed Selection semantics already fixed in the project.
5. Existing OHLC snap/calibration data from Phase 5 where available.

## Inactive / deferred sources
- YouTube video content: HOLD.
- Video transcript: HOLD.
- OpenAI API / cloud model dispatch: HOLD.
- Teacher verbal rationale not visible in the PDF: not inferred.

## Week status
- `PDF_READY`: chart material exists locally and may be parsed.
- `NO_CHART_WEEK`: no chart PDF/image exists. End the weekly path successfully; do not infer from video/fundamentals.
- `REVIEW_REQUIRED`: input is present but inconsistent/corrupt/ambiguous enough that automation should not promote a baseline.

## Evidence labels
- `TEACHER_CONFIRMED`: directly visible/explicit in Teacher chart material.
- `RULE_MATCH`: observed geometry is consistent with a currently fixed R01–R20 rule.
- `SELECTION_MATCH`: observed geometry is consistent with a currently fixed Selection semantic.
- `INFERRED`: local model inference; never upgraded to Teacher-confirmed without evidence.
- `UNKNOWN`: unsupported by the current sources.
- `VIDEO_RATIONALE_PENDING`: reason may exist in video, but video is intentionally deferred.

## Render policy
Drawing must not stop merely because Teacher rationale is unknown. Geometry can proceed when supported by the PDF, while rationale remains `UNKNOWN` / `VIDEO_RATIONALE_PENDING`.

## Non-comparable / HOLD
FIB and SCENARIO are observed Teacher objects but are not automatically generated in this version unless an existing fixed rule explicitly enables them.

## Prohibited fields / actions
The following are contract violations anywhere in the output tree:
`entry`, `entry_price`, `long_short`, `trade_direction`, `sl`, `stop_loss`, `tp`, `take_profit`, `rr`, `risk_reward`, `lot`, `order_type`, `ticket`.

No trade decision or order action may be emitted.
