# NVT9 Promotion Scope Audit — 2026-09-19

Audit ID: **ID10IQ200**  
Status: **PASS — RESPONSIBILITY-LAYER SCOPE FROZEN / NO PRODUCTION WRITEBACK**

## Audit question

Which NVT responsibility layers A-E have enough evidence to replace current Production behavior now?

## Evidence reviewed

- fixed NVT integration/promotion policy;
- Production Live Draw baseline, detector, lifecycle and Normal Run implementation;
- NVT3 real-data difference report;
- NVT6 ownership/selector research and explicit production guards;
- NVT7 scoped lifecycle freeze;
- NVT8 strict held-out teacher registry and comparator;
- executed corrected report `NVT8_STRICT_HELDOUT_COMPARISON_CORRECTED.json`.

The executed corrected NVT8 result is `PASS_STRICT_NVT8`, with all scored held-out events passing and `nvt9_promotion_review_ready=true`. The correction is limited to the TE_02 evaluation-harness label mismatch `LARGE` vs `LARGE_DOW`; no model/rule retuning occurred.

## Layer audit result

```text
A Market Facts / Turn recognition          KEEP BASELINE
B Structure ownership / Candidate gen.    KEEP BASELINE
C Structure Selector                      KEEP BASELINE
D Lifecycle / display role                KEEP BASELINE
E Renderer / style                        KEEP BASELINE
```

Implementation target set: **empty**.

## Why the empty target set is intentional

NVT9 promotion policy is evidence-gated, not architecture-gated. Strict NVT8 largely validated behavior that the existing Production baseline already executes. Replacing a passing baseline with research-only variants would violate the fixed policy that an adequately matching layer must not be rewritten merely for uniformity.

Layer B has a documented gap from NVT3/NVT6, but its candidate Production rule remains under-validated. Therefore the safe NVT9 V0.1 disposition is to preserve the baseline while carrying Layer B forward as a research backlog, not to silently promote a hypothesis.

## Protected surfaces

No change is authorized in this scope-freeze step to:

- `tools/live_draw/`;
- `mt4/NCA_NormalRun_Renderer.mq4`;
- Production `NCA_DRAW__` object semantics;
- manual-object protection;
- trade/order authority.

## Gate to final NVT9 close

Run unchanged baseline regression and MT4 verification. If those pass, close NVT9 with no Production promotion. If either fails, diagnose the exact responsibility layer before authorizing any implementation.
