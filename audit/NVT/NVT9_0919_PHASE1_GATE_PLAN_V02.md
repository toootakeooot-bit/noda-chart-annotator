# NVT9 09/19 Phase-1 Gate Plan V0.2

Audit ID: ID10IQ200  
Date: 2026-09-20  
Scope: USDJPY# / 09-19 teacher comparison

## Updated order

| Gate | Purpose | Current status |
|---|---|---|
| V0 | Freeze existing 16-object baseline | PASS |
| V1 | Explain every NCA line | IMPLEMENTED |
| V2 | Freeze 09/19 teacher evidence | PASS |
| V3 | Compare teacher assertions with NCA structure | PASS at declared NVT8 scope |
| V3.5 | Cross-timeframe structural ownership | TOOLING_COMPLETE_PENDING_LOCAL_EXECUTION_AND_ADJUDICATION |
| V4 | Derive Visibility rule after ownership | DECISION_TOOL_READY_BLOCKED_PENDING_V3.5 |
| V5 | Regression against 09/19 teacher invariants | REGRESSION_TOOL_READY_WAITING_V4_PREVIEW |
| V6 | Audit-only preview snapshot | IMPLEMENTED_WAITING_V4_POLICY |
| V7 | MT4 visual comparison | WAIT |
| V8 | Production promotion | NOT STARTED |
| V9 | Reason/audit logging | DESIGN INPUT ACTIVE; Production integration later |

## V3.5 objective

Do not assume source timeframe equals structural owner timeframe.

Review D1-H4, H4-H1, H1-M15 and export threshold-free evidence:
direction agreement, projected TL/CH gaps, slope difference, anchor differences, parent/child anchor-span hours, child/parent span ratio and channel-width-normalized gap.

The remembered "H1 -> H4 time range" is therefore measured at V3.5, but no fixed elapsed-hour boundary is permitted yet.

No automatic SAME_FAMILY threshold is allowed from 09/19 alone.

## User-observed 09/19 hypotheses

- NCA H4 primary TL corresponds to teacher D1 TL.
- NCA H1 primary TL corresponds to teacher H4 TL.
- NCA M15 primary TL corresponds to teacher H1 TL.

These are adjudication inputs, not fixed global shifts.

## V4 unblock condition

Classify each relevant lower-TF primary line as:
PARENT_OWNED_SAME_FAMILY, LOCAL_OWNED_DISTINCT, or AMBIGUOUS_KEEP_VISIBLE.

Visibility suppression may then use ownership without deleting lifecycle state.

## Safety

No Turn detector, candidate generator, selector, lifecycle, production snapshot, renderer, or NCA_DRAW__ behavior is changed in V3.5.


## 2026-09-20 tooling advance

Repository-side preparation now includes:

- threshold-free cross-TF matrix with anchor-span evidence
- conservative AUTO adjudication
- explicit override template and validated override merger
- V3.5 gate evaluator
- ownership-aware V4 decision builder
- V5 teacher-invariant regression validator
- one-shot local runner: setup\\RUN_NVT9_PHASE1_ADVANCE_0919.cmd

The next evidence-bearing step is local execution against the live MT4 state. Non-exact rows remain AMBIGUOUS_KEEP_VISIBLE until explicitly adjudicated. No Production writeback is authorized by tooling completion.
