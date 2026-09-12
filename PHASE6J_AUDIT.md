# Phase 6-J PDF-only Local Teacher Parser — audit checkpoint

## Fixed decision
- Weekly video: HOLD; not used.
- OpenAI API: HOLD; not used.
- Current-source drawing continues from PDF/chart + R01–R20 + fixed Selection semantics.
- Unknown rationale does not block drawing.
- Future 4-week video rationale mining may be added later without changing the current geometry pipeline.

## PASS gates for the next live test
1. `setup/01_install_local_pdf_only.ps1` PASS.
2. `setup/02_pull_local_vlm.ps1` PASS.
3. `setup/03_verify_local_vlm.ps1` PASS.
4. Run one existing READY package through `run_pdf_only_once.cmd`.
5. Confirm `teacher_observation.json` exists.
6. Confirm `pdf_only_status.json` = `PDF_ONLY_OBSERVATION_READY`.
7. Confirm prohibited trade fields are absent recursively.
8. For a no-chart package, confirm `NO_CHART_WEEK / PASS` and no video/API fallback.

## Not yet claimed complete
- Existing P5-5 Parser/Comparator handoff has not yet been live-tested against this v0.5 local observation schema.
- MT4 automatic render from the new local observation has not yet been live-tested.
- Teacher rationale enrichment from old videos is deferred.
