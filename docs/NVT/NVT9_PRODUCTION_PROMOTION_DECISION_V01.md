# NVT9 Production Promotion Decision V0.1

Status: **SCOPE FROZEN / NO PRODUCTION PATCH YET**  
Date: **2026-09-19**  
Audit ID: **ID10IQ200**  
Branch: `feature/nvt-validation-v1`

## 1. Purpose

Fix the NVT9 Production promotion scope by responsibility layer after corrected strict NVT8 held-out validation.

This phase is a promotion decision only. It does **not** modify:

- `tools/live_draw/`;
- Production Normal Run semantics;
- `NCA_DRAW__` ownership or object behavior;
- MT4 renderer code or MT4 objects;
- trade authority.

The current Production Normal Run remains `BASELINE_V1` and the rollback reference.

## 2. NVT8 gate entering NVT9

The corrected strict NVT8 report is the gating result:

- status: `PASS_STRICT_NVT8`;
- all four scored held-out events pass;
- `strict_nvt8_satisfied = true`;
- `nvt9_promotion_review_ready = true`;
- `production_promotion_ready = false`;
- harness correction: `NVT8_HARNESS_FIX_001`;
- the correction fixed only the evaluator label mismatch `LARGE` vs `LARGE_DOW`;
- no frozen NVT algorithm, teacher assertion, market data, or model replay was changed.

NVT9 therefore may review layer promotion, but Production writeback is not automatic.

## 3. Responsibility-layer decision

| Layer | Responsibility | Decision | Production implementation target | Basis |
|---|---|---|---|---|
| A | Market Facts / Turn recognition | **KEEP BASELINE** | None | Strict NVT8 replay used the existing Production 38% closed-bar Turn Detector. NVT7.1 explicitly reuses the existing 38% detector. A universal deterministic SMALL/MID/LARGE classifier remains unfixed, so no replacement detector is eligible. |
| B | Structure ownership / Candidate generation | **KEEP BASELINE** | None in NVT9 V0.1 | NVT3/NVT6 found a real NO-LINE / ownership and Micro-Dow recall gap, but the proposed Ownership Gate A/B/C and Micro-Dow ownership rules remain research hypotheses. Current evidence explicitly says the tested positive/negative separation is insufficient to fix a Production rule. Strict NVT8 did not independently validate that ownership gate as a held-out Production behavior. |
| C | Structure Selector | **KEEP BASELINE** | None | Strict NVT8 replay used the existing Production `build_channel_candidates` + `select_large_mid` path and passed its declared held-out scope. NVT6 selector leads still depend on DRAFT/exact-anchor-unlocked evidence and are not eligible as a hard Production selector rule. |
| D | Lifecycle / display role | **KEEP BASELINE** | None | Held-out retention/channel/local-parent checks were evaluated using Production `rebuild_timeframe_from_bars` and the current lifecycle state and passed. NVT7 adds useful research semantics, but unsupported automatic suppression thresholds, delete/retire behavior, and exact reference ownership remain deferred. No evidence requires replacing the current Production lifecycle in this promotion. |
| E | Renderer / style | **KEEP BASELINE** | None | NVT8 did not lock exact style/anchor rendering changes. Renderer/style is outside the validated improvement scope. MT4 actual rendering verification remains a later gate, not authority to change rendering now. |

## 4. NVT9 V0.1 implementation scope

```text
A  KEEP BASELINE
B  KEEP BASELINE
C  KEEP BASELINE
D  KEEP BASELINE
E  KEEP BASELINE

IMPLEMENTATION_TARGET_LAYERS = []
PRODUCTION_SEMANTIC_PATCH = NONE
RENDERER_PATCH = NONE
NCA_DRAW__ CHANGE = NONE
MT4 OBJECT WRITEBACK = NONE
```

This is a valid NVT9 result under the fixed integration policy: a research layer is not promoted merely because it exists. A Production rewrite requires a validated behavior-specific improvement over the baseline.

## 5. Known gap retained outside Production

Layer B is the only currently documented material gap that remains worth pursuing:

- Production can produce H1 line candidates in a teacher NO-LINE context;
- NVT research can restore Micro-Dow alternatives for a positive case;
- research Ownership Gates A/B/C strongly separate the currently tested GT_0006 positive and GT_0007 negative cases.

However, those rules are not Production-fixed because:

1. the ownership rule itself is explicitly still research-only;
2. exact anchors/labels remain incomplete for some development evidence;
3. strict NVT8 did not provide an independent held-out NO-LINE/ownership-gate case sufficient to generalize the rule.

Disposition:

```text
B gap = OPEN RESEARCH BACKLOG
B Production promotion = DEFERRED
Current Production B = KEEP BASELINE
```

A future NVT revision may reopen Layer B only with new independent held-out evidence. It must not tune against the already-consumed NVT8 held-out source.

## 6. NVT7 semantics retained as regression guards, not Production rewrites

The following validated/research-frozen concepts remain useful as regression guards:

- validity and visibility are separate;
- a newer geometry does not imply unconditional deletion of a useful reference;
- `EDIT_TRANSIENT` is an observation filter, not a stable market-time state;
- local structure state and parent structure promotion are separate;
- `TURN_LINE` is not automatically promoted to a visible major line.

These do not by themselves authorize a Production code change where the current baseline already satisfies the tested behavior or does not expose that object class.

## 7. Next NVT9 step

Because `IMPLEMENTATION_TARGET_LAYERS = []`, do **not** create a semantic Production patch branch yet.

Next step is a no-change closure check:

```text
freeze this A-E decision
 -> verify BASELINE_V1 regression remains PASS
 -> perform MT4 verification against unchanged renderer
 -> confirm zero NCA_DRAW__ ownership/safety regressions
 -> issue NVT9 final audit / close or reopen only the specific failing layer
```

If all checks pass, NVT9 closes as **NO PRODUCTION PROMOTION REQUIRED**.  
If a check fails, reopen only the responsibility layer identified by the failure; do not perform a whole-system rewrite.
