# NVT7.1 USDJPY Batch02 adjudication — 2026-09-17

## Scope

Research-only USDJPY historical operational validation. This note records user adjudication for the ambiguous reference-retirement cases in `NVT7_1_USDJPY_TARGETED_REVIEW_BATCH02.json`.

## User adjudication

- `USDJPY_NVT71_B02_03` (2026-06-22): the old reference **may be retired/deleted**.
- `USDJPY_NVT71_B02_04` (2026-07-02): choose **C — retain the old rising line as well**.
- `USDJPY_NVT71_B02_05` (2026-07-03): choose **C — retain the old rising line as well**.

The earlier B02_03 line-importance adjudication remains in force. In particular, drawability, importance confirmation, visibility, lifecycle state, and decision ownership remain separate dimensions.

## Research interpretation

The combined evidence sharpens the NVT7.1 lifecycle candidate:

1. `RETIRED_REFERENCE` remains a supported user-operational state because B02_03 allows retirement.
2. Retirement is **not** newest-only: B02_04/B02_05 retain the old line even when newer candidates exist.
3. Retirement is **not** gentleness-only: a gentler redraw may coexist with the older rising reference.
4. A local `FALLING` leg does not by itself retire the older rising reference.
5. When evidence is ambiguous, retain the reference until its structural role is clearly subsumed.

No numeric retirement threshold is fixed by this batch.

## Guardrails

- Do not rewrite the frozen NVT7 scoped beta in place.
- Do not treat this user operational evidence as teacher Ground Truth.
- Do not promote `RETIRED_REFERENCE` to an automatic deletion rule.
- Do not modify Production Normal Run, MT4 `NCA_DRAW__` objects, or trading authority.

## Next check

Run `RUN_NVT7_1_USDJPY_BATCH02_FINALIZE.cmd`. The expected handoff is:

`%APPDATA%\MetaQuotes\Terminal\Common\Files\noda_draw\nvt_output\nvt7_1_batch02_final\NVT7_1_BATCH02_FINAL_HANDOFF.json`

A pass means the Batch01 + Batch02 research contracts are internally consistent. It does not mean Production promotion is ready.
