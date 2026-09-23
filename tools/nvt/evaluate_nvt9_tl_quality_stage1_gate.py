from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

REQUIRED_HISTORY_CASES = {"GT_0004", "GT_0005", "GT_0006", "GT_0007"}


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def iter_lines(payload: dict[str, Any]):
    for tf, tf_payload in (payload.get("timeframes") or {}).items():
        for row in tf_payload.get("lines") or []:
            if isinstance(row, dict):
                yield str(tf), row


def line_gate(tf: str, row: dict[str, Any]) -> dict[str, Any]:
    audit = row.get("quality_audit") or {}
    ownership = row.get("ownership_evidence") or {}
    failures: list[dict[str, Any]] = []

    def fail(code: str, detail: str) -> None:
        failures.append({"code": code, "detail": detail})

    quality = audit.get("Quality")
    core_ready = audit.get("AuditReadiness")
    owner_ready = audit.get("OwnershipReadiness")
    match_status = row.get("match_status")
    owner_confirmed = ownership.get("owner_confirmed")
    ownership_ambiguous = ownership.get("ownership_ambiguous")
    parent_family_unresolved = ownership.get("parent_family_unresolved")

    if quality != "GOOD":
        fail("QUALITY_NOT_GOOD", f"Quality={quality!r}")
    if core_ready != "READY":
        fail("CORE_AUDIT_NOT_READY", f"AuditReadiness={core_ready!r}")
    if owner_ready != "PASS":
        fail("OWNERSHIP_NOT_PASS", f"OwnershipReadiness={owner_ready!r}")
    if match_status != "EXACT_UNIQUE":
        fail("CANDIDATE_JOIN_NOT_EXACT_UNIQUE", f"match_status={match_status!r}")
    if owner_confirmed is not True:
        fail("OWNER_NOT_CONFIRMED", f"owner_confirmed={owner_confirmed!r}")
    if ownership_ambiguous is True:
        fail("OWNERSHIP_AMBIGUOUS", "ownership_ambiguous=true")
    if parent_family_unresolved is True:
        fail(
            "PARENT_FAMILY_UNRESOLVED",
            "Owner timeframe may be confirmed, but exact parent-family identity is unresolved.",
        )

    hold_or_bad_reasons = [
        reason
        for reason in audit.get("reasons") or []
        if isinstance(reason, dict) and reason.get("disposition") in {"HOLD", "BAD"}
    ]
    if hold_or_bad_reasons:
        fail(
            "AUDIT_HAS_NON_GOOD_FINDING",
            ",".join(str(x.get("reason_code")) for x in hold_or_bad_reasons),
        )

    return {
        "source_tf": tf,
        "line_id": row.get("line_id"),
        "generation_role": row.get("generation_role"),
        "structure_level": row.get("structure_level"),
        "quality": quality,
        "core_readiness": core_ready,
        "ownership_readiness": owner_ready,
        "match_status": match_status,
        "ownership_classification": ownership.get("classification"),
        "owner_tf": ownership.get("owner_tf"),
        "owner_confirmed": owner_confirmed,
        "ownership_ambiguous": ownership_ambiguous,
        "parent_family_unresolved": parent_family_unresolved,
        "stage1_line_ready": not failures,
        "failures": failures,
    }


def history_gate(history: dict[str, Any] | None) -> dict[str, Any]:
    if history is None:
        return {
            "supplied": False,
            "ready": False,
            "failures": [
                {
                    "code": "HISTORY_REPLAY_NOT_SUPPLIED",
                    "detail": "Historical replay is required before Stage-2 design eligibility.",
                }
            ],
        }

    failures: list[dict[str, Any]] = []
    teacher_cases = {
        str(x.get("case_id"))
        for x in history.get("teacher_cases") or []
        if isinstance(x, dict) and x.get("case_id")
    }
    missing = sorted(REQUIRED_HISTORY_CASES - teacher_cases)
    if missing:
        failures.append({
            "code": "REQUIRED_HISTORY_CASES_MISSING",
            "detail": ",".join(missing),
        })

    gaps = history.get("unresolved_evidence_gaps") or []
    if gaps:
        failures.append({
            "code": "HISTORY_EVIDENCE_GAPS_REMAIN",
            "detail": f"{len(gaps)} unresolved evidence gap(s)",
        })

    user_0905 = history.get("user_adjudication_0905_transition") or {}
    if user_0905:
        if user_0905.get("exact_anchor_geometry_locked") is not True:
            failures.append({
                "code": "0905_EXACT_GEOMETRY_NOT_LOCKED",
                "detail": "09/05 transition semantics are adjudicated, but exact replay geometry is still unlocked.",
            })
    else:
        failures.append({
            "code": "0905_TRANSITION_ADJUDICATION_MISSING",
            "detail": "09/05 transition adjudication is required.",
        })

    unresolved_conflicts = [
        x for x in history.get("superseded_or_conflicting_history") or []
        if isinstance(x, dict) and str(x.get("status") or "").upper() not in {"SUPERSEDED", "RESOLVED"}
    ]
    if unresolved_conflicts:
        failures.append({
            "code": "HISTORY_CONFLICT_UNRESOLVED",
            "detail": f"{len(unresolved_conflicts)} conflict(s) are not superseded/resolved.",
        })

    return {
        "supplied": True,
        "ready": not failures,
        "required_case_count": len(REQUIRED_HISTORY_CASES),
        "present_case_count": len(teacher_cases & REQUIRED_HISTORY_CASES),
        "missing_cases": missing,
        "unresolved_evidence_gap_count": len(gaps),
        "0905_exact_geometry_locked": user_0905.get("exact_anchor_geometry_locked"),
        "failures": failures,
    }


def evaluate(
    *,
    ownership_join: dict[str, Any],
    history_replay: dict[str, Any] | None,
    all_generations: bool = False,
) -> dict[str, Any]:
    targeted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for tf, row in iter_lines(ownership_join):
        role = str(row.get("generation_role") or "")
        if not all_generations and role != "CURRENT":
            skipped.append({
                "source_tf": tf,
                "line_id": row.get("line_id"),
                "generation_role": role,
                "reason": "NON_CURRENT_EXCLUDED_FROM_STAGE1_GATE",
            })
            continue
        targeted.append(line_gate(tf, row))

    line_failures = [x for x in targeted if not x["stage1_line_ready"]]
    history_result = history_gate(history_replay)

    global_failures: list[dict[str, Any]] = []
    if not targeted:
        global_failures.append({
            "code": "NO_TARGET_LINES",
            "detail": "No CURRENT TLs were available for Stage-1 readiness evaluation.",
        })
    if line_failures:
        global_failures.append({
            "code": "LINE_GATES_BLOCKED",
            "detail": f"{len(line_failures)} target line(s) failed Stage-1 readiness.",
        })
    if not history_result["ready"]:
        global_failures.append({
            "code": "HISTORY_GATE_BLOCKED",
            "detail": f"{len(history_result['failures'])} history gate failure(s).",
        })

    ready = not global_failures
    status = "PASS_STAGE1_READY_FOR_STAGE2_DESIGN" if ready else "BLOCKED_STAGE1"

    failure_codes = Counter(
        failure["code"]
        for row in line_failures
        for failure in row.get("failures") or []
    )
    history_failure_codes = Counter(
        failure["code"] for failure in history_result.get("failures") or []
    )

    return {
        "schema": "nvt9-tl-quality-stage1-gate/1.0",
        "status": status,
        "audit_id": "ID10IQ200",
        "source_join_schema": ownership_join.get("schema"),
        "source_join_status": ownership_join.get("status"),
        "target_scope": "ALL_GENERATIONS" if all_generations else "CURRENT_ONLY",
        "target_line_count": len(targeted),
        "ready_line_count": len(targeted) - len(line_failures),
        "blocked_line_count": len(line_failures),
        "skipped_line_count": len(skipped),
        "line_failure_code_counts": dict(failure_codes),
        "history_failure_code_counts": dict(history_failure_codes),
        "history_gate": history_result,
        "global_failures": global_failures,
        "lines": targeted,
        "skipped_lines": skipped,
        "stage2_design_eligible": ready,
        "automatic_reselection_enabled": False,
        "automatic_reselection_note": (
            "PASS only permits Stage-2 design/held-out testing. It never enables automatic Candidate replacement or Production writeback."
        ),
        "policy": {
            "all_target_lines_must_pass": True,
            "numeric_pass_percentage_threshold_used": False,
            "quality_required": "GOOD",
            "core_audit_required": "READY",
            "ownership_required": "PASS",
            "candidate_join_required": "EXACT_UNIQUE",
            "owner_confirmation_required": True,
            "ownership_ambiguity_allowed": False,
            "parent_family_unresolved_allowed": False,
            "required_history_cases": sorted(REQUIRED_HISTORY_CASES),
            "0905_exact_geometry_required": True,
        },
        "production_writeback": False,
        "renderer_writeback": False,
        "state_mutated": False,
        "mt4_object_writeback": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Evaluate NVT9 Stage-1 TL Quality readiness before any Stage-2 automatic re-selection design."
    )
    ap.add_argument("--ownership-join", required=True)
    ap.add_argument("--history-replay", required=True)
    ap.add_argument("--all-generations", action="store_true")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    result = evaluate(
        ownership_join=load_json(Path(args.ownership_join)) or {},
        history_replay=load_json(Path(args.history_replay)),
        all_generations=bool(args.all_generations),
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "target_line_count": result["target_line_count"],
        "ready_line_count": result["ready_line_count"],
        "blocked_line_count": result["blocked_line_count"],
        "history_ready": result["history_gate"]["ready"],
        "stage2_design_eligible": result["stage2_design_eligible"],
        "automatic_reselection_enabled": False,
        "output": str(out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
