# NVT9 USDJPY MT4 Smoke Preparation Audit

Status: **READY FOR HOST MT4 VERIFICATION**  
Date: **2026-09-19**  
Audit ID: **ID10IQ200**  
Branch: `feature/nvt-validation-v1`

## Purpose

Prepare the shortest host-side verification path for the unchanged Production `BASELINE_V1` on `USDJPY#`.

This work does **not** modify Production market semantics, renderer semantics, `tools/live_draw/`, or existing MT4 drawing ownership.

## NVT9 scope guard

The runner refuses to continue unless `nvt/manifests/NVT9_PROMOTION_SCOPE_V01.json` still declares:

- A-E = `KEEP BASELINE`;
- no implementation target layers;
- no Production semantic patch;
- no renderer patch;
- no `NCA_DRAW__` change;
- no MT4 object writeback authorized by NVT9.

## Added host helpers

- `setup/RUN_NVT9_USDJPY_MT4_SMOKE.cmd`
- `setup/run_nvt9_usdjpy_mt4_smoke.ps1`

The PowerShell runner:

1. checks the frozen NVT9 no-change scope;
2. requires fresh MT4 Normal Run export files for D1/H4/H1/M15;
3. invokes the existing `NR7-1` baseline regression and safe-snapshot checks;
4. verifies that Normal Run reports `PASS` and publishes a validated snapshot;
5. writes `NVT9_USDJPY#_MT4_SMOKE_READY.json` in MT4 Common Files `live_output`;
6. prints expected renderer row counts for D1/H4/H1/M15;
7. leaves the final host action as unchanged MT4 rendering and visual verification.

## Required host sequence

1. Open `USDJPY#` in MT4.
2. Run `NCA_NormalRun_Exporter` once.
3. Run `setup/RUN_NVT9_USDJPY_MT4_SMOKE.cmd`.
4. If the CMD reports automated PASS, run unchanged `NCA_NormalRun_Renderer` once on each:
   - D1
   - H4
   - H1
   - M15
5. Capture the four chart screenshots for final NVT9 host review.

## Safety boundary

- Existing `NCA_DRAW__` renderer behavior is unchanged.
- Manual/non-NCA chart objects remain outside renderer ownership.
- No trading fields or order actions are introduced.
- No NVT research rule is promoted by this preparation step.

## Closure condition

NVT9 is **not closed** by this commit alone.

Final closure requires actual host evidence that the unchanged renderer produces the expected Baseline drawing on MT4 without a drawing safety regression.
