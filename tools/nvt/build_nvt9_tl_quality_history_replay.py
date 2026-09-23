from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from tl_quality_auditor import audit_line

ROOT = Path(__file__).resolve().parents[2]

TEACHER_CASE_RULES = {
    "GT_0004": {
        "market_date": "2026-09-05",
        "patterns": ["P16"],
        "teacher_expectation": "KEEP_ORIGINAL_RISING_REFERENCE",
        "layer": "LIFECYCLE",
    },
    "GT_0005": {
        "market_date": "2026-09-12",
        "patterns": ["P17"],
        "teacher_expectation": "VALID_BUT_DISPLAY_SUPPRESSED",
        "layer": "LIFECYCLE",
    },
    "GT_0006": {
        "market_date": "2026-09-12",
        "patterns": ["P18", "P19"],
        "teacher_expectation": "PREFER_GENTLER_VALID_LINE",
        "layer": "SELECTOR",
    },
    "GT_0007": {
        "market_date": "2026-08-08",
        "patterns": ["P20"],
        "teacher_expectation": "NO_H1_TL_INTERNAL_LINE_BELONGS_TO_M15",
        "layer": "OWNERSHIP",
    },
}


def load_json(path: Path | None) -> Any:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def valid_0905_transition_lock(payload: dict[str, Any] | None) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if not isinstance(payload, dict):
        return False, ["LOCK_NOT_SUPPLIED"]
    if payload.get("schema") != "nvt9-0905-transition-exact-replay/1.0":
        failures.append("BAD_SCHEMA")
    if payload.get("case_date") != "2026-09-05":
        failures.append("BAD_CASE_DATE")
    if payload.get("cutoff_exclusive") != "2026-09-05T00:00:00":
        failures.append("BAD_CUTOFF")
    if payload.get("status") != "PASS_0905_TRANSITION_EXACT_REPLAY":
        failures.append("LOCK_STATUS_NOT_PASS")
    if payload.get("transition_exact_geometry_locked") is not True:
        failures.append("TRANSITION_GEOMETRY_NOT_LOCKED")
    lock = payload.get("lock") or {}
    if lock.get("transition_exact_geometry_locked") is not True:
        failures.append("INNER_LOCK_NOT_TRUE")
    if lock.get("failed_checks"):
        failures.append("FAILED_CHECKS_PRESENT")
    return not failures, failures


def walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def find_case(payload: Any, case_id: str) -> dict[str, Any] | None:
    if payload is None:
        return None
    candidates = [
        item
        for item in walk_dicts(payload)
        if item.get("case_id") == case_id and ("mode" in item or "status" in item)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda x: len(x), reverse=True)
    return candidates[0]


def first_final_state_rows(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    for item in walk_dicts(payload):
        rows = item.get("final_state_rows")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def owner_hypotheses(cross_tf: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in cross_tf.get("0919_user_observation_hypotheses") or []:
        if not isinstance(row, dict):
            continue
        source = row.get("source_tf")
        owner = row.get("teacher_owner_candidate")
        if source and owner:
            out[str(source)] = str(owner)
    return out


def infer_anchor_kind(direction: str) -> str:
    return "LOW" if str(direction).upper() == "RISING" else "HIGH"


def candidate_to_audit_record(
    candidate: dict[str, Any],
    *,
    line_id: str,
    source_tf: str,
    structure_level: str = "MID_DOW",
    teacher_window_absent: bool = False,
) -> dict[str, Any]:
    direction = str(candidate.get("direction") or "")
    return {
        "line_id": line_id,
        "direction": direction,
        "source_tf": source_tf,
        "owner_tf": source_tf,
        "structure_level": structure_level,
        "anchor1": candidate.get("anchor1") or {},
        "anchor2": candidate.get("anchor2") or {},
        "turn_span": candidate.get("turn_span"),
        "tl_contacts": candidate.get("tl_contacts"),
        "ch_contacts": candidate.get("ch_contacts"),
        "unbroken_close": candidate.get("unbroken_close"),
        "ch_offset": candidate.get("ch_offset"),
        "zone_width": candidate.get("zone_width"),
        "candidate": {
            "teacher_window_absent_diagnostic": teacher_window_absent,
        },
    }


def cross_line_to_audit_record(
    line: dict[str, Any],
    *,
    expected_owner: str | None,
) -> dict[str, Any]:
    source_tf = str(line.get("timeframe") or "")
    direction = str(line.get("direction") or "")
    anchor_kind = infer_anchor_kind(direction)
    owner_tf = expected_owner or source_tf

    record: dict[str, Any] = {
        "line_id": line.get("line_id"),
        "direction": direction,
        "source_tf": source_tf,
        "owner_tf": owner_tf,
        "structure_level": line.get("structure_level"),
        "anchor1": {
            "kind": anchor_kind,
            "time": line.get("anchor1_time"),
            "price": line.get("anchor1_price"),
        },
        "anchor2": {
            "kind": anchor_kind,
            "time": line.get("anchor2_time"),
            "price": line.get("anchor2_price"),
        },
        "ch_offset": line.get("ch_offset"),
        "zone_width": line.get("zone_width"),
        "lifecycle": line.get("status"),
    }

    if expected_owner and expected_owner != source_tf:
        record["cross_tf"] = {
            "mapping_allowed": True,
            "owner_confirmed": False,
            "ownership_ambiguous": True,
        }
    return record


def replay_0919_cross_tf(
    cross_tf: dict[str, Any] | None,
    strict_heldout: dict[str, Any] | None,
) -> dict[str, Any]:
    if cross_tf is None:
        return {
            "status": "NOT_SUPPLIED",
            "line_count": 0,
            "audits": [],
        }

    owner_map = owner_hypotheses(cross_tf)
    audits: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []

    for tf, rows in (cross_tf.get("current_line_sets") or {}).items():
        if not isinstance(rows, list):
            continue
        for line in rows:
            if not isinstance(line, dict):
                continue
            expected_owner = owner_map.get(str(tf))
            record = cross_line_to_audit_record(line, expected_owner=expected_owner)
            result = audit_line(record)
            result["replay_source"] = "NVT9_USDJPY_CROSS_TF_0919"
            result["source_line_status"] = line.get("status")
            result["expected_owner_from_user_observation"] = expected_owner
            audits.append(result)
            source_rows.append(line)

    strict_rows = first_final_state_rows(strict_heldout)
    strict_ids = {str(row.get("line_id")) for row in strict_rows if row.get("line_id")}
    cross_ids = {str(row.get("line_id")) for row in source_rows if row.get("line_id")}
    joined = sorted(cross_ids & strict_ids)

    quality_counts = Counter(item["Quality"] for item in audits)
    readiness_counts = Counter(item["AuditReadiness"] for item in audits)
    missing = Counter()
    for item in audits:
        missing.update(item.get("missing_evidence") or [])

    return {
        "status": "REPLAYED",
        "source_schema": cross_tf.get("schema"),
        "source_status": cross_tf.get("status"),
        "line_count": len(audits),
        "quality_counts": dict(quality_counts),
        "readiness_counts": dict(readiness_counts),
        "missing_evidence_counts": dict(missing),
        "strict_heldout_context": {
            "supplied": strict_heldout is not None,
            "status": strict_heldout.get("status") if isinstance(strict_heldout, dict) else None,
            "strict_nvt8_satisfied": strict_heldout.get("strict_nvt8_satisfied") if isinstance(strict_heldout, dict) else None,
            "final_state_row_count": len(strict_rows),
            "line_id_join_count": len(joined),
            "joined_line_ids": joined,
            "join_note": (
                "Strict held-out PASS is retained as global context only. It is not used to force current cross-TF lines to GOOD."
            ),
        },
        "audits": audits,
    }


def ground_truth_case(
    gt: dict[str, Any],
    probe: dict[str, Any] | None,
) -> dict[str, Any]:
    case_id = str(gt.get("case_id"))
    rule = TEACHER_CASE_RULES[case_id]
    notes = [str(x) for x in (gt.get("notes") or [])]
    probe_status = probe.get("status") if isinstance(probe, dict) else None

    conflict = None
    if case_id == "GT_0005" and probe_status == "NO_LINE_CONFIRMED_BY_TEACHER_EVIDENCE":
        conflict = {
            "status": "SUPERSEDED",
            "older_interpretation": "NO_LINE_CONFIRMED_BY_TEACHER_EVIDENCE",
            "newer_ground_truth": "VALID_BUT_DISPLAY_SUPPRESSED",
            "resolution": (
                "Use reviewed GT_0005 semantics: the TURN_LINE is structurally valid but intentionally not displayed. "
                "Retain the older probe as superseded evidence."
            ),
        }

    return {
        "case_id": case_id,
        "source_id": gt.get("source_id"),
        "market_date": rule["market_date"],
        "timeframe": gt.get("timeframe"),
        "annotation_status": gt.get("annotation_status"),
        "source_confidence": gt.get("source_confidence"),
        "teacher_expectation": rule["teacher_expectation"],
        "patterns": rule["patterns"],
        "primary_layer": rule["layer"],
        "teacher_object_count": len(gt.get("teacher_objects") or []),
        "notes": notes,
        "probe_status": probe_status,
        "probe_mode": probe.get("mode") if isinstance(probe, dict) else None,
        "probe_conflict": conflict,
    }


def replay_probe_candidates(
    probe_payload: Any,
    case_id: str,
) -> dict[str, Any]:
    probe = find_case(probe_payload, case_id)
    if probe is None:
        return {"case_id": case_id, "status": "PROBE_NOT_SUPPLIED", "audits": []}

    candidates: list[dict[str, Any]]
    teacher_window_absent = False
    if case_id == "GT_0006":
        candidates = [
            x for x in (probe.get("nearest_when_window_not_exact") or [])
            if isinstance(x, dict)
        ]
        teacher_window_absent = probe.get("status") == "ABSENT_WITHIN_WINDOWS"
    else:
        candidates = [x for x in (probe.get("matches") or []) if isinstance(x, dict)]

    audits = []
    for index, candidate in enumerate(candidates, start=1):
        record = candidate_to_audit_record(
            candidate,
            line_id=f"{case_id}_CANDIDATE_{index:03d}",
            source_tf=str(probe.get("timeframe") or ""),
            teacher_window_absent=teacher_window_absent,
        )
        result = audit_line(record)
        result["candidate_id"] = candidate.get("candidate_id")
        result["replay_case_id"] = case_id
        audits.append(result)

    return {
        "case_id": case_id,
        "status": probe.get("status"),
        "mode": probe.get("mode"),
        "eligible_candidate_count": probe.get("eligible_candidate_count"),
        "window_match_count": probe.get("window_match_count"),
        "audited_candidate_count": len(audits),
        "quality_counts": dict(Counter(x["Quality"] for x in audits)),
        "readiness_counts": dict(Counter(x["AuditReadiness"] for x in audits)),
        "audits": audits,
    }


def load_gt(gt_dir: Path, case_id: str) -> dict[str, Any]:
    path = gt_dir / f"{case_id}.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def build_replay(
    *,
    gt_dir: Path,
    teacher_anchor_probe: dict[str, Any] | None,
    cross_tf_0919: dict[str, Any] | None,
    strict_heldout_0919: dict[str, Any] | None,
    user_0905: dict[str, Any] | None,
    transition_lock_0905: dict[str, Any] | None = None,
) -> dict[str, Any]:
    teacher_cases = []
    probe_index = {}
    for case_id in TEACHER_CASE_RULES:
        gt = load_gt(gt_dir, case_id)
        probe = find_case(teacher_anchor_probe, case_id)
        teacher_cases.append(ground_truth_case(gt, probe))
        probe_index[case_id] = probe

    candidate_replays = [
        replay_probe_candidates(teacher_anchor_probe, "GT_0004"),
        replay_probe_candidates(teacher_anchor_probe, "GT_0006"),
    ]

    conflicts = [
        case["probe_conflict"]
        for case in teacher_cases
        if case.get("probe_conflict")
    ]

    user_transition = None
    lock_valid, lock_failures = valid_0905_transition_lock(transition_lock_0905)
    if isinstance(user_0905, dict):
        source_locked = user_0905.get("exact_anchor_geometry_locked") is True
        effective_locked = source_locked or lock_valid
        user_transition = {
            "case_id": user_0905.get("case_id"),
            "market_date": user_0905.get("market_date"),
            "scope": user_0905.get("scope"),
            "pattern_id": user_0905.get("pattern_id"),
            "quality_expectation_during_middle_state": user_0905.get("quality_expectation_during_middle_state"),
            "exact_anchor_geometry_locked": effective_locked,
            "source_adjudication_exact_anchor_geometry_locked": source_locked,
            "transition_exact_replay_lock_applied": lock_valid,
            "transition_exact_replay_lock_failures": lock_failures,
            "transition_exact_replay_status": (
                transition_lock_0905.get("status") if isinstance(transition_lock_0905, dict) else None
            ),
            "transition_exact_replay_cutoff": (
                transition_lock_0905.get("cutoff_exclusive") if isinstance(transition_lock_0905, dict) else None
            ),
            "transition_rule": user_0905.get("transition_rule"),
        }

    replay_0919 = replay_0919_cross_tf(cross_tf_0919, strict_heldout_0919)

    unresolved: list[str] = []
    if replay_0919.get("line_count"):
        if replay_0919.get("readiness_counts", {}).get("READY", 0) < replay_0919["line_count"]:
            unresolved.append(
                "0919 current-line artifact does not carry all per-line Pivot/HL/N/Dow/closed-break evidence required for READY audits."
            )
        if replay_0919["strict_heldout_context"].get("supplied") and replay_0919["strict_heldout_context"].get("line_id_join_count") == 0:
            unresolved.append(
                "0919 strict-heldout lifecycle line IDs do not directly join to the cross-TF current-line IDs; global PASS cannot be assigned line-by-line."
            )
    if user_transition and not user_transition.get("exact_anchor_geometry_locked"):
        unresolved.append(
            "0905 H1/M15 NO-LINE transition is semantically adjudicated but exact replay anchors/geometry remain unfrozen."
        )

    return {
        "schema": "nvt9-tl-quality-history-replay/1.0",
        "audit_id": "ID10IQ200",
        "status": "PARTIAL_REAL_HISTORY_REPLAY_COMPLETE",
        "policy": {
            "teacher_expectation_separate_from_generated_quality": True,
            "history_does_not_override_hard_gate": True,
            "automatic_correction": False,
        },
        "teacher_cases": teacher_cases,
        "user_adjudication_0905_transition": user_transition,
        "candidate_replays": candidate_replays,
        "replay_0919_current_lines": replay_0919,
        "superseded_or_conflicting_history": conflicts,
        "unresolved_evidence_gaps": unresolved,
        "next_gate": (
            "Persist per-line retracement confirmation, HL/N/Dow state, break_by_close, Candidate rank/selection reason and ownership evidence "
            "in the live history artifact; then rerun this replay until READY coverage is sufficient."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay real NVT teacher/history artifacts through TL Quality Auditor")
    ap.add_argument("--gt-dir", default=str(ROOT / "nvt" / "ground_truth"))
    ap.add_argument("--teacher-anchor-probe")
    ap.add_argument("--cross-tf-0919")
    ap.add_argument("--strict-heldout-0919")
    ap.add_argument("--transition-lock-0905")
    ap.add_argument(
        "--user-0905",
        default=str(ROOT / "nvt" / "adjudication" / "NVT9_USER_0905_TRANSITION_V01.json"),
    )
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    result = build_replay(
        gt_dir=Path(args.gt_dir),
        teacher_anchor_probe=load_json(Path(args.teacher_anchor_probe)) if args.teacher_anchor_probe else None,
        cross_tf_0919=load_json(Path(args.cross_tf_0919)) if args.cross_tf_0919 else None,
        strict_heldout_0919=load_json(Path(args.strict_heldout_0919)) if args.strict_heldout_0919 else None,
        user_0905=load_json(Path(args.user_0905)) if args.user_0905 else None,
        transition_lock_0905=load_json(Path(args.transition_lock_0905)) if args.transition_lock_0905 else None,
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": result["status"],
        "teacher_case_count": len(result["teacher_cases"]),
        "candidate_replay_count": len(result["candidate_replays"]),
        "0919_line_count": result["replay_0919_current_lines"].get("line_count", 0),
        "history_conflict_count": len(result["superseded_or_conflicting_history"]),
        "unresolved_gap_count": len(result["unresolved_evidence_gaps"]),
        "output": str(out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
