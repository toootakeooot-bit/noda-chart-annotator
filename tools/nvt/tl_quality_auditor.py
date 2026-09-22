from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Literal

Quality = Literal["GOOD", "HOLD", "BAD"]
Confidence = Literal["HIGH", "MEDIUM", "LOW"]
CheckState = Literal["PASS", "FAIL", "HOLD", "UNKNOWN"]
Layer = Literal[
    "PIVOT",
    "ANCHOR",
    "STRUCTURE",
    "CANDIDATE_GENERATION",
    "SELECTOR",
    "OWNERSHIP",
    "LIFECYCLE",
    "RENDERER",
    "GEOMETRY",
    "HISTORY",
]

QUALITY_SCHEMA = "nvt9-tl-quality-audit/1.0"
AUDITOR_VERSION = "NVT9_TL_QUALITY_AUDITOR_V01"
MAJOR_LEVELS = {"LARGE_DOW", "MID_DOW", "LARGE_DOW_TL", "MID_DOW_TL"}


@dataclass(frozen=True)
class Finding:
    pattern_id: str | None
    layer: Layer
    reason_code: str
    disposition: Quality
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _first(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


def _nested(record: dict[str, Any], key: str) -> dict[str, Any]:
    value = record.get(key)
    return value if isinstance(value, dict) else {}


def _bool(record: dict[str, Any], nested: dict[str, Any], *keys: str) -> bool | None:
    value = _first(nested, *keys, default=None)
    if value is None:
        value = _first(record, *keys, default=None)
    return value if isinstance(value, bool) else None


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_direction(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).upper()
    aliases = {
        "UP": "RISING",
        "ASCENDING": "RISING",
        "BULL": "RISING",
        "DOWN": "FALLING",
        "DESCENDING": "FALLING",
        "BEAR": "FALLING",
    }
    return aliases.get(text, text if text in {"RISING", "FALLING"} else None)


def _normalize_level(record: dict[str, Any]) -> str | None:
    value = _first(record, "structure_level", "dow_level", "level", "line_role")
    return str(value).upper() if value is not None else None


def _anchor(record: dict[str, Any], which: str) -> dict[str, Any]:
    direct = record.get(which)
    if isinstance(direct, dict):
        return direct
    prefix = f"{which}_"
    out = {}
    for key, value in record.items():
        if key.startswith(prefix):
            out[key[len(prefix):]] = value
    return out


def _pivot_state(anchor: dict[str, Any]) -> tuple[CheckState, list[str]]:
    if not anchor:
        return "UNKNOWN", ["anchor evidence missing"]

    reasons: list[str] = []
    explicit_valid = _first(anchor, "pivot_valid", "valid_pivot")
    if explicit_valid is False:
        reasons.append("explicit pivot validity is false")
        return "FAIL", reasons

    retracement = _float(_first(anchor, "retracement", "retracement_ratio", "retrace"))
    if retracement is not None and retracement + 1e-12 < 0.38:
        reasons.append(f"retracement {retracement:.6g} < 0.38")
        return "FAIL", reasons

    closed = _first(anchor, "closed_bar_confirmed", "confirmed_on_closed_bar")
    if closed is False:
        reasons.append("pivot depends on an unclosed bar")
        return "FAIL", reasons

    confirmed_by = _first(anchor, "confirmed_by_time", "confirmed_time")
    if retracement is not None or explicit_valid is True or confirmed_by is not None:
        return "PASS", reasons
    return "UNKNOWN", ["no 38%/confirmation evidence supplied"]


def _anchor_state(
    direction: str | None,
    anchor1: dict[str, Any],
    anchor2: dict[str, Any],
    record: dict[str, Any],
) -> tuple[CheckState, list[str]]:
    if not anchor1 or not anchor2:
        return "UNKNOWN", ["two anchors are not fully supplied"]

    reasons: list[str] = []
    expected_kind = "LOW" if direction == "RISING" else "HIGH" if direction == "FALLING" else None
    for idx, anchor in enumerate((anchor1, anchor2), start=1):
        kind = _first(anchor, "kind", "pivot_kind")
        if expected_kind and kind is not None and str(kind).upper() != expected_kind:
            reasons.append(f"anchor{idx} kind {kind!s} != expected {expected_kind}")
            return "FAIL", reasons

    spacing_valid = _first(record, "anchor_spacing_valid")
    if spacing_valid is False:
        return "FAIL", ["anchor spacing explicitly invalid"]
    span = _float(_first(record, "turn_span"))
    if span is not None and span <= 0:
        return "FAIL", [f"turn_span {span:.6g} is not positive"]

    return "PASS", reasons


def _history_matches(record: dict[str, Any]) -> list[str]:
    value = _first(record, "matched_pattern", "matched_patterns", "history_matches", default=[])
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    history = _nested(record, "history")
    value = _first(history, "matched_pattern", "matched_patterns", default=[])
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def _add(
    findings: list[Finding],
    *,
    pattern_id: str | None,
    layer: Layer,
    reason_code: str,
    disposition: Quality,
    message: str,
) -> None:
    findings.append(
        Finding(
            pattern_id=pattern_id,
            layer=layer,
            reason_code=reason_code,
            disposition=disposition,
            message=message,
        )
    )


def audit_line(record: dict[str, Any]) -> dict[str, Any]:
    """Audit one generated TL without mutating candidate/selector/render state.

    The auditor consumes evidence already produced by NVT9 or by a replay
    harness. Missing evidence is conservative: it lowers confidence and may
    produce HOLD, but it never fabricates teacher truth.
    """

    line_id = str(_first(record, "TL_ID", "tl_id", "line_id", default="UNIDENTIFIED_TL"))
    direction = _normalize_direction(_first(record, "direction"))
    level = _normalize_level(record)
    source_tf = _first(record, "source_tf", "timeframe")
    owner_tf = _first(record, "owner_tf", "display_tf", "structural_owner_tf")

    anchor1 = _anchor(record, "anchor1")
    anchor2 = _anchor(record, "anchor2")
    pivot1_state, pivot1_notes = _pivot_state(anchor1)
    pivot2_state, pivot2_notes = _pivot_state(anchor2)

    if "FAIL" in {pivot1_state, pivot2_state}:
        pivot_state: CheckState = "FAIL"
    elif pivot1_state == pivot2_state == "PASS":
        pivot_state = "PASS"
    else:
        pivot_state = "UNKNOWN"

    anchor_state, anchor_notes = _anchor_state(direction, anchor1, anchor2, record)

    structure = _nested(record, "structure")
    geometry = _nested(record, "geometry")
    outer = _nested(record, "outer_inner")
    cross_tf = _nested(record, "cross_tf")
    candidate = _nested(record, "candidate")
    selector = _nested(record, "selector")
    renderer = _nested(record, "renderer")
    lifecycle = _nested(record, "lifecycle_evidence")

    findings: list[Finding] = []
    matched_patterns = _history_matches(record)

    candidate_present = _bool(record, candidate, "teacher_equivalent_candidate_present", "candidate_present")
    if candidate_present is False:
        _add(
            findings,
            pattern_id="P13",
            layer="CANDIDATE_GENERATION",
            reason_code="CANDIDATE_GENERATION_ERROR",
            disposition="BAD",
            message="Teacher-equivalent/required TL is absent from the candidate pool.",
        )

    selector_match = _bool(record, selector, "selected_candidate_matches_teacher", "selector_match")
    if candidate_present is True and selector_match is False:
        _add(
            findings,
            pattern_id="P12",
            layer="SELECTOR",
            reason_code="SELECTOR_ERROR",
            disposition="BAD",
            message="A required candidate exists but Selector chose a different TL.",
        )

    selected_correct = _bool(record, renderer, "selected_correctly")
    visible = _bool(record, renderer, "visible", "rendered")
    renderer_match = _bool(record, renderer, "renderer_match")
    if renderer_match is False or (selected_correct is True and visible is False):
        _add(
            findings,
            pattern_id=None,
            layer="RENDERER",
            reason_code="RENDERER_ERROR",
            disposition="BAD",
            message="Correct selection evidence exists but the TL is not rendered as required.",
        )

    if pivot_state == "FAIL":
        _add(
            findings,
            pattern_id=None,
            layer="PIVOT",
            reason_code="PIVOT_ERROR",
            disposition="BAD",
            message="At least one anchor fails the 38%/closed-bar Pivot gate.",
        )
    if anchor_state == "FAIL":
        _add(
            findings,
            pattern_id=None,
            layer="ANCHOR",
            reason_code="ANCHOR_ERROR",
            disposition="BAD",
            message="Anchor pair is incompatible with direction/spacing requirements.",
        )

    outer_candidate_exists = _bool(record, outer, "outer_candidate_exists", "important_outer_anchor_exists")
    selected_outer = _bool(record, outer, "selected_outer", "outer_structure_selected")
    major_wick_outside = _bool(record, outer, "major_wick_outside", "major_structure_outside")
    if outer_candidate_exists is True and (selected_outer is False or major_wick_outside is True):
        _add(
            findings,
            pattern_id="P03",
            layer="ANCHOR",
            reason_code="OUTER_STRUCTURE_MISMATCH",
            disposition="BAD",
            message="An important outer structure exists but an inner TL was selected or major structure remains outside.",
        )
    elif outer_candidate_exists is True and selected_outer is True:
        matched_patterns.append("P02")

    prior_tl_broken = _bool(record, structure, "prior_tl_broken", "old_tl_broken")
    new_structure_ready = _bool(record, structure, "new_structure_ready", "new_tl_structure_ready")
    dow_confirmed = _bool(record, structure, "dow_confirmed", "dow_structure_confirmed")
    n_confirmed = _bool(record, structure, "n_pattern_confirmed", "n_structure_confirmed")
    hl_exists = _bool(record, structure, "hl_exists", "hl_confirmed")
    hl_break = _bool(record, structure, "hl_break", "hl_broken")
    break_by_close = _bool(record, structure, "break_by_close", "closed_bar_break")
    activated_on_wick = _bool(record, structure, "activated_on_wick_only")
    small_dow_only = _bool(record, structure, "small_dow_only", "local_dow_only")

    if prior_tl_broken is True and new_structure_ready is False:
        _add(
            findings,
            pattern_id="P04",
            layer="STRUCTURE",
            reason_code="NO_LINE_HOLD",
            disposition="HOLD",
            message="Previous TL is broken, but the next TL structure is not yet complete.",
        )

    if hl_break is True and break_by_close is False:
        disposition: Quality = "BAD" if activated_on_wick is True else "HOLD"
        _add(
            findings,
            pattern_id="P06",
            layer="STRUCTURE",
            reason_code="WICK_ONLY_BREAK",
            disposition=disposition,
            message="HL penetration is wick-only; closed-bar break confirmation is absent.",
        )
    elif hl_break is True and break_by_close is True:
        matched_patterns.append("P07")

    if small_dow_only is True and level in MAJOR_LEVELS:
        _add(
            findings,
            pattern_id="P14",
            layer="STRUCTURE",
            reason_code="SMALL_DOW_MAJOR_PROMOTION",
            disposition="BAD",
            message="Small-Dow evidence alone cannot promote a new Large/Mid major TL.",
        )

    explicit_structure_checks = [v for v in (hl_exists, n_confirmed, dow_confirmed) if v is not None]
    if explicit_structure_checks and False in explicit_structure_checks and prior_tl_broken is not True:
        _add(
            findings,
            pattern_id=None,
            layer="STRUCTURE",
            reason_code="STRUCTURE_EVIDENCE_INCOMPLETE",
            disposition="HOLD",
            message="Required HL/N/Dow evidence is explicitly incomplete.",
        )

    if (
        prior_tl_broken is True
        and new_structure_ready is True
        and dow_confirmed is True
        and hl_break is True
        and break_by_close is True
    ):
        matched_patterns.append("P05")

    precedence_basis = _first(selector, "precedence_basis", default=_first(record, "precedence_basis"))
    latest_only = _bool(record, selector, "latest_only_override")
    if latest_only is True or (isinstance(precedence_basis, str) and precedence_basis.upper() == "LATEST_ONLY"):
        _add(
            findings,
            pattern_id="P15",
            layer="SELECTOR",
            reason_code="LATEST_ONLY_PRECEDENCE",
            disposition="BAD",
            message="TL precedence is based only on recency, ignoring still-valid older structure.",
        )

    if source_tf is not None and owner_tf is not None and str(source_tf) != str(owner_tf):
        mapping_allowed = _bool(record, cross_tf, "mapping_allowed", "cross_tf_allowed")
        owner_confirmed = _bool(record, cross_tf, "owner_confirmed", "ownership_confirmed")
        ownership_ambiguous = _bool(record, cross_tf, "ownership_ambiguous", "ambiguous")
        if mapping_allowed is True and owner_confirmed is True:
            matched_patterns.append("P08")
        elif ownership_ambiguous is True or owner_confirmed is False:
            _add(
                findings,
                pattern_id="P09",
                layer="OWNERSHIP",
                reason_code="OWNERSHIP_UNRESOLVED",
                disposition="HOLD",
                message="Cross-timeframe mapping is plausible but ownership evidence is unresolved.",
            )
        elif mapping_allowed is False:
            _add(
                findings,
                pattern_id=None,
                layer="OWNERSHIP",
                reason_code="OWNERSHIP_ERROR",
                disposition="BAD",
                message="Requested source_tf to owner_tf mapping is explicitly disallowed.",
            )

    lifecycle_value = _first(record, "lifecycle", "generation_role", default=_first(lifecycle, "state"))
    if lifecycle_value is not None:
        life = str(lifecycle_value).upper()
        if life in {"REFERENCE_RETAINED", "PREVIOUS", "RETAINED"}:
            matched_patterns.append("P10")
        if life in {"REANCHORED_CURRENT", "REANCHORED"} or _bool(record, lifecycle, "reanchored") is True:
            matched_patterns.append("P11")

    if _bool(record, lifecycle, "persistent_reference_retained") is True:
        matched_patterns.append("P16")

    candidate_valid = _bool(record, lifecycle, "candidate_valid")
    display_suppressed = _bool(record, lifecycle, "display_suppressed", "valid_suppressed")
    line_role = _first(lifecycle, "line_role", default=_first(record, "line_role"))
    if (
        candidate_valid is True
        and display_suppressed is True
        and line_role is not None
        and str(line_role).upper() == "TURN_LINE"
    ):
        matched_patterns.append("P17")

    gentler_preference = _bool(record, selector, "gentler_preference_satisfied")
    multiple_valid_alternatives = _bool(record, selector, "multiple_valid_alternatives")
    if gentler_preference is True:
        matched_patterns.append("P18")
    elif gentler_preference is False and multiple_valid_alternatives is True:
        _add(
            findings,
            pattern_id="P18",
            layer="SELECTOR",
            reason_code="GENTLER_PREFERENCE_MISMATCH",
            disposition="BAD",
            message="Multiple valid TL alternatives exist but Selector did not preserve the teacher-adjudicated gentler-angle preference.",
        )

    if _bool(record, candidate, "teacher_window_absent_diagnostic") is True:
        _add(
            findings,
            pattern_id="P19",
            layer="CANDIDATE_GENERATION",
            reason_code="TEACHER_WINDOW_ABSENT_DIAGNOSTIC",
            disposition="HOLD",
            message="No candidate was found in the reviewed teacher anchor windows; exact anchors remain non-locking, so this is diagnostic HOLD rather than hard BAD.",
        )

    unbroken_close = _first(geometry, "unbroken_close", default=_first(record, "unbroken_close"))
    geometry_state: CheckState = "UNKNOWN"
    geometry_notes: list[str] = []
    if unbroken_close is True:
        geometry_state = "PASS"
    elif unbroken_close is False:
        geometry_state = "HOLD"
        geometry_notes.append("TL has a closed-bar violation; structural context must justify retention/re-anchor.")
    else:
        geom_fields = (
            _first(record, "turn_span"),
            _first(record, "tl_contacts"),
            _first(record, "slope_per_second", "slope"),
            _first(record, "ch_offset"),
            _first(record, "zone_width"),
        )
        if any(v is not None for v in geom_fields):
            geometry_state = "PASS"

    core_structure_positive = all(
        v is True for v in (hl_exists, n_confirmed, dow_confirmed, hl_break, break_by_close)
    )
    if level in MAJOR_LEVELS and pivot_state == "PASS" and anchor_state == "PASS" and core_structure_positive:
        matched_patterns.append("P01")

    if any(f.layer == "STRUCTURE" and f.disposition == "BAD" for f in findings):
        structure_state: CheckState = "FAIL"
    elif any(f.layer == "STRUCTURE" and f.disposition == "HOLD" for f in findings):
        structure_state = "HOLD"
    elif core_structure_positive:
        structure_state = "PASS"
    else:
        structure_state = "UNKNOWN"

    if hl_break is True and break_by_close is True:
        hl_break_state: CheckState = "PASS"
    elif hl_break is True and break_by_close is False:
        hl_break_state = "HOLD"
    elif hl_break is False:
        hl_break_state = "HOLD"
    else:
        hl_break_state = "UNKNOWN"

    if any(f.reason_code == "OUTER_STRUCTURE_MISMATCH" for f in findings):
        outer_state: CheckState = "FAIL"
    elif outer_candidate_exists is True and selected_outer is True:
        outer_state = "PASS"
    else:
        outer_state = "UNKNOWN"

    if any(f.layer == "OWNERSHIP" and f.disposition == "BAD" for f in findings):
        cross_tf_state: CheckState = "FAIL"
    elif any(f.layer == "OWNERSHIP" and f.disposition == "HOLD" for f in findings):
        cross_tf_state = "HOLD"
    elif source_tf is not None and owner_tf is not None and str(source_tf) != str(owner_tf):
        cross_tf_state = "PASS" if "P08" in matched_patterns else "UNKNOWN"
    else:
        cross_tf_state = "PASS" if source_tf is not None else "UNKNOWN"

    matched_patterns = list(dict.fromkeys(matched_patterns))
    negative_pattern_ids = {"P03", "P04", "P06", "P09", "P12", "P13", "P14", "P15", "P19"}
    positive_pattern_ids = {"P01", "P02", "P05", "P07", "P08", "P10", "P11", "P16", "P17", "P18"}
    historical_positive = [p for p in matched_patterns if p in positive_pattern_ids]
    historical_negative = [p for p in matched_patterns if p in negative_pattern_ids]
    history_state: CheckState = "PASS" if historical_positive else "HOLD" if historical_negative else "UNKNOWN"

    bad_findings = [f for f in findings if f.disposition == "BAD"]
    hold_findings = [f for f in findings if f.disposition == "HOLD"]

    if bad_findings:
        quality: Quality = "BAD"
    elif hold_findings:
        quality = "HOLD"
    else:
        sufficient_core = pivot_state == "PASS" and anchor_state == "PASS" and structure_state == "PASS"
        if sufficient_core:
            quality = "GOOD"
        else:
            quality = "HOLD"
            _add(
                findings,
                pattern_id=None,
                layer="HISTORY",
                reason_code="INSUFFICIENT_AUDIT_EVIDENCE",
                disposition="HOLD",
                message="No hard failure found, but core Pivot/Anchor/Structure evidence is incomplete.",
            )
            hold_findings = [f for f in findings if f.disposition == "HOLD"]

    if quality == "BAD":
        confidence: Confidence = "HIGH" if bad_findings else "MEDIUM"
    elif quality == "HOLD":
        explicit_hold = any(f.reason_code != "INSUFFICIENT_AUDIT_EVIDENCE" for f in hold_findings)
        confidence = "HIGH" if explicit_hold and pivot_state != "UNKNOWN" else "MEDIUM"
        if not explicit_hold and pivot_state == "UNKNOWN" and anchor_state == "UNKNOWN":
            confidence = "LOW"
    else:
        all_core_pass = (
            pivot_state == "PASS"
            and anchor_state == "PASS"
            and structure_state == "PASS"
            and hl_break_state == "PASS"
        )
        confidence = "HIGH" if all_core_pass and bool(historical_positive) else "MEDIUM"

    primary = None
    if bad_findings:
        primary = bad_findings[0].layer
    elif hold_findings:
        primary = hold_findings[0].layer

    checks = {
        "Pivot": pivot_state,
        "Anchor": anchor_state,
        "Structure": structure_state,
        "HL Break": hl_break_state,
        "Geometry": geometry_state,
        "Outer/Inner": outer_state,
        "Cross-TF": cross_tf_state,
        "History Match": history_state,
    }

    core_readiness = {
        "Pivot": pivot_state,
        "Anchor": anchor_state,
        "Structure": structure_state,
        "HL Break": hl_break_state,
    }
    missing_evidence = [name for name, state in core_readiness.items() if state == "UNKNOWN"]
    known_core_count = sum(state != "UNKNOWN" for state in core_readiness.values())
    if not missing_evidence:
        audit_readiness = "READY"
    elif known_core_count:
        audit_readiness = "PARTIAL"
    else:
        audit_readiness = "INSUFFICIENT"

    return {
        "schema": QUALITY_SCHEMA,
        "auditor_version": AUDITOR_VERSION,
        "TL_ID": line_id,
        "direction": direction,
        "source_tf": source_tf,
        "owner_tf": owner_tf,
        "structure_level": level,
        "Quality": quality,
        "Confidence": confidence,
        "AuditReadiness": audit_readiness,
        "missing_evidence": missing_evidence,
        "cause_layer": primary,
        "checks": checks,
        "matched_patterns": matched_patterns,
        "reasons": [f.to_dict() for f in findings],
        "evidence_notes": {
            "pivot_anchor1": pivot1_notes,
            "pivot_anchor2": pivot2_notes,
            "anchor": anchor_notes,
            "geometry": geometry_notes,
        },
        "source_evidence": {
            "candidate_rank": _first(record, "candidate_rank", default=_first(candidate, "rank")),
            "selector_reason": _first(record, "selector_reason", "selection_reason", default=_first(selector, "reason")),
            "turn_span": _first(record, "turn_span"),
            "tl_contacts": _first(record, "tl_contacts", "contacts"),
            "ch_contacts": _first(record, "ch_contacts"),
            "slope": _first(record, "slope_per_second", "slope"),
            "unbroken_close": unbroken_close,
            "ch_offset": _first(record, "ch_offset"),
            "zone_width": _first(record, "zone_width"),
            "price_distance": _first(record, "price_distance"),
        },
    }


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        raise ValueError("input JSON must be an object or array")
    for key in ("lines", "records", "selected_lines", "objects", "candidates"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    return [payload]


def audit_lines(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    audits = [audit_line(record) for record in records]
    counts = {"GOOD": 0, "HOLD": 0, "BAD": 0}
    for item in audits:
        counts[item["Quality"]] += 1
    return {
        "schema": "nvt9-tl-quality-audit-batch/1.0",
        "auditor_version": AUDITOR_VERSION,
        "record_count": len(audits),
        "quality_counts": counts,
        "audits": audits,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NVT9 audit-only TL Quality Auditor. Does not modify Production drawing state."
    )
    parser.add_argument("--input", required=True, help="JSON line/candidate/history input")
    parser.add_argument("--output", required=True, help="Output audit JSON")
    args = parser.parse_args()

    src = Path(args.input)
    payload = json.loads(src.read_text(encoding="utf-8"))
    result = audit_lines(_extract_records(payload))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "auditor": AUDITOR_VERSION,
        "record_count": result["record_count"],
        "quality_counts": result["quality_counts"],
        "output": str(out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
