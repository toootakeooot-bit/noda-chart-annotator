# NVT8 Held-out Preflight Audit — 2026-09-16

Status: **BLOCKED / NO CLEAN SOURCE-LEVEL HELD-OUT VIDEO IN CURRENT CORPUS**

## Trigger

NVT7 scoped lifecycle beta completed its frozen-scope regression and reported `held_out_validation_ready=true` for the frozen lifecycle scope. The next fixed roadmap stage is NVT8 independent video validation.

## Strict hold-out rule

NVT8 is interpreted as source-level independent video validation. A source video is not clean held-out material if it was inspected, registered, or used as development evidence in NVT0-NVT7, even if only one segment from that video was used.

## Current five-video corpus

| Source | Development/touch evidence | Clean held-out? |
|---|---|---|
| NVT_VIDEO_20260808 | GT_0001 / GT_0002 / GT_0007 | NO |
| NVT_VIDEO_20260822 | NVT1 OBS_0007 hierarchy/procedure evidence | NO |
| NVT_VIDEO_20260830 | GT_0003 and additional observations | NO |
| NVT_VIDEO_20260905 | GT_0004 | NO |
| NVT_VIDEO_20260912 | GT_0005 / GT_0006 | NO |

The key correction is `NVT_VIDEO_20260822`: although it was not a lifecycle tuning case, it was already reviewed and registered as `OBS_0007`. It must therefore not be relabeled retroactively as a clean source-level held-out video.

## Additional material

A 2026-08-15 PDF exists, but the fixed NVT8 roadmap requires independent **video** validation. The PDF may be useful as supporting material, but it cannot by itself satisfy the NVT8 video gate.

## Result

```text
NVT7 SCOPED BETA FROZEN: PASS
NVT7 FROZEN SCOPE REGRESSION: PASS
NVT8 SOURCE-LEVEL HOLDOUT AVAILABLE: NO
NVT8 INDEPENDENT VIDEO VALIDATION: BLOCKED
PRODUCTION PROMOTION: NOT READY
PRODUCTION WRITEBACK: NO
```

## Required next evidence

Add at least one previously unseen video source. Before any teacher-event inspection, register that source as held-out. It must then be frozen to actual broker closed-bar history, annotated without tuning the frozen NVT rules, and scored by failure layer against both the NVT beta and current NCA baseline.

A future weekly analysis video, or an older video that has genuinely not been reviewed anywhere in NVT0-NVT7, can satisfy the source-level independence requirement.

## Implementation added

- `nvt/manifests/NVT8_SOURCE_PARTITION_V1.json`
- `tools/nvt/check_nvt8_holdout_preflight.py`
- `setup/run_nvt8_holdout_preflight.ps1`
- `setup/RUN_NVT8_HELD_OUT_PREFLIGHT.cmd`

The preflight returns a generated `BLOCKED` research result with exit code 0 when the only blocker is lack of a clean held-out source. This distinguishes an expected evidence gate from a runner failure.

No production `tools/live_draw/`, `NCA_DRAW__`, Normal Run behavior, or MT4 object state was changed.
