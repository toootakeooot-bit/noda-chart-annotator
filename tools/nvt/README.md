# NVT Tools

Research / validation tools for NODA Visual Teacher.

This directory is isolated from production `tools/live_draw/` during NVT0-NVT8.

Planned stage ownership:

```text
extract_event.py       NVT4 video event extraction
replay_to_time.py      NVT5 time-frozen replay
dump_candidates.py     NVT2 candidate dump
compare_teacher.py     NVT3 teacher-vs-NCA diff
scoring.py             NVT3+ validation metrics
```

These tools must not modify production NCA semantics before NVT9 promotion.
