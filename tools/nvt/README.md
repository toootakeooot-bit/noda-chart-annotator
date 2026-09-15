# NVT Tools

Research / validation tools for NODA Visual Teacher.

This directory is isolated from production `tools/live_draw/` during NVT0-NVT8.

Stage ownership:

```text
extract_event.py       NVT4 video event extraction        PLACEHOLDER
replay_to_time.py      NVT5 time-frozen replay            PLACEHOLDER
dump_candidates.py     NVT2 candidate dump                IMPLEMENTED v1
compare_teacher.py     NVT3 teacher-vs-NCA diff           PLACEHOLDER
scoring.py             NVT3+ validation metrics           PLACEHOLDER
```

`dump_candidates.py` is read-only research tooling. It reuses the current production detector/candidate builder/selector and emits JSON for analysis; it does not modify state, snapshot, MT4 objects, or trade behavior.

These tools must not modify production NCA semantics before NVT9 promotion.
