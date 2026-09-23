from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "nvt"))

from tl_quality_auditor import audit_line

CONFIRMED_CLASSIFICATIONS = {
    "PARENT_OWNED_SAME_FAMILY",
    "HIGHER_TF_OWNER_PARENT_UNRESOLVED",
    "LOCAL_OWNED_DISTINCT",
}
AMBIGUOUS_CLASSIFICATIONS = {"AMBIGUOUS_KEEP_VISIBLE"}


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def ownership_index(payload: dict[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in payload.get("records") or []:
        if not isinstance(rec, dict):
            continue
        source_tf = rec.get("source_tf")
        line_id = rec.get("line_id")
        if source_tf and line_id:
            out[(str(source_tf), str(line_id))] = rec
    return out


def gate_index(payload: dict[str, Any] | None) -> dict[tuple[str | None, str], dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    out: dict[tuple[str | None, str], dict[str, Any]] = {}
    for bucket in ("problems", "unresolved", "parent_match_unresolved"):
        for item in payload.get(bucket) or []:
            if not isinstance(item, dict) or not item.get("line_id"):
                continue
            key = (item.get("source_tf"), str(item.get("line_id")))
            entry = out.setdefault(key, {"buckets": [], "items": []})
            entry["buckets"].append(bucket)
            entry["items"].append(dict(item))
    return out


def owner_confidence(rec: dict[str, Any], classification: str) -> str:
    relation = str(rec.get("relation") or "").upper()
    note = rec.get("teacher_evidence_note")
    override = rec.get("override_applied") is True
    if classification == "PARENT_OWNED_SAME_FAMILY":
        if relation == "AUTO_EXACT_GEOMETRY" or note or override:
            return "HIGH"
        return "MEDIUM"
    if classification == "HIGHER_TF_OWNER_PARENT_UNRESOLVED":
        return "HIGH" if note or override else "MEDIUM"
    if classification == "LOCAL_OWNED_DISTINCT":
        return "HIGH" if note else "MEDIUM"
    return "LOW"


def ownership_evidence(
    *,
    source_tf: str,
    line_id: str,
    rec: dict[str, Any] | None,
    gate: dict[str, Any] | None,
) -> dict[str, Any]:
    # D1 has no higher parent in the supported NVT9 hierarchy. Absence of a
    # child->parent adjudication row is therefore a confirmed native/root owner.
    if rec is None and source_tf == "D1":
        return {
            "classification": "ROOT_LOCAL_OWNED",
            "source_tf": source_tf,
            "line_id": line_id,
            "owner_tf": source_tf,
            "candidate_owner_tf": None,
            "mapping_allowed": True,
            "owner_confirmed": True,
            "ownership_ambiguous": False,
            "same_family_parent_id": None,
            "parent_family_confirmed": False,
            "parent_family_unresolved": False,
            "confidence": "HIGH",
            "reason_code": "ROOT_TIMEFRAME_NATIVE_OWNER",
            "relation": "NO_HIGHER_PARENT_IN_SUPPORTED_HIERARCHY",
            "display_policy": "DRAW_LOCAL_STRUCTURE",
            "gate": gate,
        }

    if rec is None:
        return {
            "classification": "OWNERSHIP_RECORD_MISSING",
            "source_tf": source_tf,
            "line_id": line_id,
            "owner_tf": source_tf,
            "candidate_owner_tf": None,
            "mapping_allowed": True,
            "owner_confirmed": False,
            "ownership_ambiguous": True,
            "same_family_parent_id": None,
            "parent_family_confirmed": False,
            "parent_family_unresolved": True,
            "confidence": "LOW",
            "reason_code": "OWNERSHIP_RECORD_MISSING",
            "relation": "SOURCE_TF_VISIBILITY_FALLBACK_ONLY",
            "display_policy": "KEEP_VISIBLE",
            "gate": gate,
        }

    classification = str(rec.get("classification") or "")
    structural_owner = str(rec.get("structural_owner_tf") or source_tf)
    candidate_owner = rec.get("user_observed_owner_candidate_tf") or rec.get("best_metric_parent_tf")
    ambiguous = classification in AMBIGUOUS_CLASSIFICATIONS or rec.get("adjudication_required") is True
    confirmed = classification in CONFIRMED_CLASSIFICATIONS and not ambiguous
    owner_tf = structural_owner if confirmed else source_tf
    same_family_parent_id = rec.get("same_family_parent_id")

    gate_buckets = set((gate or {}).get("buckets") or [])
    if "problems" in gate_buckets or "unresolved" in gate_buckets:
        confirmed = False
        ambiguous = True
        owner_tf = source_tf

    parent_unresolved = (
        classification == "HIGHER_TF_OWNER_PARENT_UNRESOLVED"
        or "parent_match_unresolved" in gate_buckets
    )

    return {
        "classification": classification or "UNCLASSIFIED",
        "source_tf": source_tf,
        "line_id": line_id,
        "owner_tf": owner_tf,
        "candidate_owner_tf": candidate_owner,
        "mapping_allowed": True,
        "owner_confirmed": confirmed,
        "ownership_ambiguous": ambiguous,
        "same_family_parent_id": same_family_parent_id,
        "parent_family_confirmed": bool(
            classification == "PARENT_OWNED_SAME_FAMILY" and same_family_parent_id and confirmed
        ),
        "parent_family_unresolved": bool(parent_unresolved),
        "confidence": owner_confidence(rec, classification) if confirmed else "LOW",
        "reason_code": rec.get("reason_code"),
        "relation": rec.get("relation"),
        "display_policy": rec.get("display_recommendation") or "KEEP_VISIBLE",
        "teacher_evidence_note": rec.get("teacher_evidence_note"),
        "override_applied": rec.get("override_applied") is True,
        "gate": gate,
    }


def audit_record_from_sidecar_row(
    row: dict[str, Any],
    ownership: dict[str, Any],
) -> dict[str, Any]:
    source_tf = str(row.get("timeframe") or ownership.get("source_tf") or "")
    state = row.get("state_geometry") or {}
    candidate = row.get("candidate")
    selector = dict(row.get("selector_evidence") or {})
    role = str(row.get("generation_role") or "")

    # Final full-history Selector is authoritative only for CURRENT rows.
    if role != "CURRENT":
        selector["selector_match"] = None

    record: dict[str, Any] = {
        "line_id": row.get("line_id"),
        "direction": state.get("direction") or (candidate or {}).get("direction"),
        "source_tf": source_tf,
        "owner_tf": ownership.get("owner_tf") or source_tf,
        "structure_level": row.get("structure_level"),
        "selector": selector,
        "cross_tf": {
            "classification": ownership.get("classification"),
            "relation": ownership.get("relation"),
            "candidate_owner_tf": ownership.get("candidate_owner_tf"),
            "mapping_allowed": ownership.get("mapping_allowed"),
            "owner_confirmed": ownership.get("owner_confirmed"),
            "ownership_ambiguous": ownership.get("ownership_ambiguous"),
            "parent_family_confirmed": ownership.get("parent_family_confirmed"),
            "parent_family_unresolved": ownership.get("parent_family_unresolved"),
            "ownership_confidence": ownership.get("confidence"),
        },
        "lifecycle_evidence": {"state": role},
    }

    if isinstance(candidate, dict):
        break_by_close = bool(candidate.get("break_by_close"))
        record.update({
            "anchor1": candidate.get("anchor1") or {},
            "anchor2": candidate.get("anchor2") or {},
            "turn_span": candidate.get("turn_span"),
            "tl_contacts": candidate.get("tl_contacts"),
            "ch_contacts": candidate.get("ch_contacts"),
            "slope_per_second": candidate.get("slope_per_second"),
            "unbroken_close": candidate.get("unbroken_close"),
            "ch_offset": candidate.get("ch_offset"),
            "zone_width": candidate.get("zone_width"),
            "candidate": {
                "candidate_present": True,
                "candidate_id": candidate.get("candidate_id"),
            },
            "structure": {
                "hl_exists": candidate.get("decision_hl") is not None,
                "n_pattern_confirmed": candidate.get("decision_hl") is not None,
                "dow_confirmed": candidate.get("decision_hl") is not None and break_by_close,
                "hl_break": candidate.get("hl_break_time") is not None,
                "break_by_close": break_by_close,
                "activated_on_wick_only": False if break_by_close else None,
            },
            "matched_patterns": ["P07"] if break_by_close else [],
        })
    else:
        # Preserve conservative HOLD semantics for an unmatched state TL. Do
        # not set candidate_present=False, because the missing final-history
        # join does not prove Candidate Generation was wrong at its replay prefix.
        record.update({
            "anchor1": {
                "kind": None,
                "time": state.get("anchor1_time"),
                "price": state.get("anchor1_price"),
            },
            "anchor2": {
                "kind": None,
                "time": state.get("anchor2_time"),
                "price": state.get("anchor2_price"),
            },
            "ch_offset": state.get("ch_offset"),
            "zone_width": state.get("zone_width"),
            "candidate": {
                "candidate_join_status": row.get("match_status"),
            },
        })

    return record


def iter_sidecar_lines(payload: dict[str, Any]):
    for tf, tf_payload in (payload.get("timeframes") or {}).items():
        for row in tf_payload.get("lines") or []:
            if isinstance(row, dict):
                yield str(tf), row


def build_join(
    *,
    evidence: dict[str, Any],
    ownership: dict[str, Any],
    gate: dict[str, Any] | None,
) -> dict[str, Any]:
    own_index = ownership_index(ownership)
    g_index = gate_index(gate)

    joined_timeframes: dict[str, dict[str, Any]] = {}
    flat: list[dict[str, Any]] = []

    for tf, row in iter_sidecar_lines(evidence):
        line_id = str(row.get("line_id") or "")
        gate_rec = g_index.get((tf, line_id)) or g_index.get((None, line_id))
        own = ownership_evidence(
            source_tf=tf,
            line_id=line_id,
            rec=own_index.get((tf, line_id)),
            gate=gate_rec,
        )
        audit_record = audit_record_from_sidecar_row(row, own)
        final_audit = audit_line(audit_record)

        joined = dict(row)
        joined["pre_ownership_quality_audit"] = row.get("quality_audit")
        joined["ownership_evidence"] = own
        joined["quality_audit"] = final_audit
        joined["ownership_delta"] = {
            "quality_before": (row.get("quality_audit") or {}).get("Quality"),
            "quality_after": final_audit.get("Quality"),
            "cross_tf_before": ((row.get("quality_audit") or {}).get("checks") or {}).get("Cross-TF"),
            "cross_tf_after": (final_audit.get("checks") or {}).get("Cross-TF"),
        }
        joined_timeframes.setdefault(tf, {"timeframe": tf, "lines": []})["lines"].append(joined)
        flat.append(joined)

    quality_counts = Counter((x.get("quality_audit") or {}).get("Quality") for x in flat)
    core_readiness_counts = Counter((x.get("quality_audit") or {}).get("AuditReadiness") for x in flat)
    ownership_readiness_counts = Counter((x.get("quality_audit") or {}).get("OwnershipReadiness") for x in flat)
    ownership_class_counts = Counter((x.get("ownership_evidence") or {}).get("classification") for x in flat)
    owner_tf_counts = Counter((x.get("ownership_evidence") or {}).get("owner_tf") for x in flat)
    unresolved = [
        {
            "source_tf": x.get("timeframe"),
            "line_id": x.get("line_id"),
            "classification": (x.get("ownership_evidence") or {}).get("classification"),
            "candidate_owner_tf": (x.get("ownership_evidence") or {}).get("candidate_owner_tf"),
            "reason_code": (x.get("ownership_evidence") or {}).get("reason_code"),
        }
        for x in flat
        if (x.get("ownership_evidence") or {}).get("ownership_ambiguous") is True
    ]

    for tf, tf_payload in joined_timeframes.items():
        tf_payload["line_count"] = len(tf_payload["lines"])
        tf_payload["quality_counts"] = dict(Counter(
            (x.get("quality_audit") or {}).get("Quality") for x in tf_payload["lines"]
        ))
        tf_payload["ownership_readiness_counts"] = dict(Counter(
            (x.get("quality_audit") or {}).get("OwnershipReadiness") for x in tf_payload["lines"]
        ))

    return {
        "schema": "nvt9-tl-quality-ownership-join/1.0",
        "status": "PASS_OWNERSHIP_JOIN" if flat else "EMPTY_OWNERSHIP_JOIN",
        "audit_id": "ID10IQ200",
        "symbol": evidence.get("symbol") or ownership.get("symbol"),
        "source_evidence_schema": evidence.get("schema"),
        "source_ownership_schema": ownership.get("schema"),
        "source_ownership_status": ownership.get("status"),
        "source_gate_schema": gate.get("schema") if isinstance(gate, dict) else None,
        "source_gate_status": gate.get("status") if isinstance(gate, dict) else None,
        "line_count": len(flat),
        "quality_counts": dict(quality_counts),
        "core_readiness_counts": dict(core_readiness_counts),
        "ownership_readiness_counts": dict(ownership_readiness_counts),
        "ownership_classification_counts": dict(ownership_class_counts),
        "owner_tf_counts": dict(owner_tf_counts),
        "ownership_unresolved_count": len(unresolved),
        "ownership_unresolved": unresolved,
        "timeframes": joined_timeframes,
        "policy": {
            "ambiguous_source_tf_fallback_is_not_confirmation": True,
            "ambiguous_keep_visible_quality": "HOLD",
            "parent_owned_same_family": "CONFIRMED",
            "higher_tf_owner_parent_unresolved": "OWNER_CONFIRMED_PARENT_FAMILY_UNRESOLVED",
            "local_owned_distinct": "CONFIRMED_LOCAL",
            "d1_missing_child_parent_record": "CONFIRMED_ROOT_NATIVE_OWNER",
            "numeric_similarity_threshold_used": False,
            "elapsed_hour_threshold_used": False,
        },
        "production_writeback": False,
        "renderer_writeback": False,
        "state_mutated": False,
        "mt4_object_writeback": False,
        "automatic_reselection": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Join NVT9 per-TL audit evidence with cross-TF ownership adjudication."
    )
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--ownership", required=True)
    ap.add_argument("--gate")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    result = build_join(
        evidence=load_json(Path(args.evidence)) or {},
        ownership=load_json(Path(args.ownership)) or {},
        gate=load_json(Path(args.gate)) if args.gate else None,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "line_count": result["line_count"],
        "quality_counts": result["quality_counts"],
        "ownership_readiness_counts": result["ownership_readiness_counts"],
        "ownership_unresolved_count": result["ownership_unresolved_count"],
        "output": str(out),
        "production_writeback": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
