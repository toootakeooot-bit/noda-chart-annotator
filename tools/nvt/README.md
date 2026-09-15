# NVT Tools

Research / validation tools for NODA Visual Teacher.

This directory is isolated from production `tools/live_draw/` during NVT0-NVT8.

Stage ownership:

```text
extract_event.py       NVT4 video event extraction        PLACEHOLDER
replay_to_time.py      NVT5 time-frozen replay            IMPLEMENTED v1
dump_candidates.py     NVT2 candidate dump                IMPLEMENTED v1
compare_teacher.py     NVT3 teacher-vs-NCA diff           IMPLEMENTED v1
scoring.py             NVT3+ validation metrics           IMPLEMENTED v1
```

## Implemented behavior

`dump_candidates.py`
- read-only candidate-pool dump at an optional frozen cutoff;
- reuses production detector / candidate builder / selector without changing them;
- exposes anchors, contacts, slope, break evidence, wick/body morphology, and current baseline selections.

`compare_teacher.py`
- compares one Ground Truth case with one NVT2 candidate dump;
- diagnoses symbol/timeframe mismatch, NO-LINE mismatch, candidate absence, anchor match, and baseline selection mismatch;
- does not convert missing teacher anchors into a false failure; unresolved exact anchors remain `PENDING_GROUND_TRUTH`;
- accepts only the explicit research notation difference `USDJPY` <-> `USDJPY#`; broader symbol alias guessing is prohibited.

`scoring.py`
- aggregates decomposed metrics only;
- reports structure-scale, candidate recall, anchor, selection-given-candidate, NO-LINE, and channel metrics when assessable;
- intentionally does not emit one aggregate promotion score.

`replay_to_time.py`
- creates a frozen OHLC CSV containing only bars at or before a verified case cutoff;
- records source/frozen SHA256, excluded-future-bar count, and `look_ahead_guard=PASS`;
- runs current baseline detector/candidate/selector on the frozen history for audit only;
- never writes production state, snapshot, MT4 objects, or trade state.

## Data isolation

NVT historical market data is exported by the research-only MT4 script:

```text
mt4/NCA_NVT_HistoryExporter.mq4
```

into:

```text
MetaQuotes/Terminal/Common/Files/noda_draw/nvt_input
```

This is intentionally separate from production Normal Run `live_input` because the initial 40-day USDJPY video corpus needs deeper H1/M15 history than the production 600-bar Normal Run export guarantees.

NVT tools must not modify production state, snapshot, `NCA_DRAW__`, manual MT4 objects, or trade behavior before NVT9 promotion.
