# NVT7 One-Click Pipeline Audit — 2026-09-16

Status: **IMPLEMENTED / RESEARCH ONLY**

## Purpose

Reduce repeated user-side NVT7 work from repeated `git pull` + stage runner + multiple artifact uploads to one stable entry point plus one handoff bundle upload.

## Entry point

`setup/RUN_NVT7_ONE_CLICK.cmd`

The command invokes `setup/run_nvt7_one_click.ps1`.

## Safety behavior

- requires branch `feature/nvt-validation-v1`;
- refuses automatic pull when the repository has local changes;
- uses `git pull --ff-only` only;
- reads `setup/NVT7_PIPELINE.json` after pull, allowing future NVT7 stages to be appended without changing the user's entry point;
- stops on the first failed required stage;
- writes research outputs only under MetaQuotes Common Files `noda_draw/nvt_output`;
- does not modify Production Normal Run, `tools/live_draw`, `NCA_DRAW__`, MT4 production objects, or trade behavior.

## Current manifested stage

- `NVT7-1-2`: lifecycle preflight + event/state graph via `setup/run_nvt7_prepare.ps1`.

Future NVT7 sequential regression / beta-freeze research stages should be appended to `setup/NVT7_PIPELINE.json` so the same one-click entry point continues to work.

## Handoff

The runner creates one file:

`nvt_output/nvt7_handoff/NVT7_HANDOFF_BUNDLE.json`

The bundle contains:

- branch / HEAD;
- stage execution results;
- currently listed NVT7 JSON artifacts embedded as structured JSON;
- explicit production-writeback guards.

The user normally needs to upload only this bundle for the next audit/research iteration.

## Limitation

This consolidates deterministic/mechanical execution. It does not bypass research decision gates where a generated result must be reviewed before the next lifecycle hypothesis is designed. Those decisions remain explicit by design.
