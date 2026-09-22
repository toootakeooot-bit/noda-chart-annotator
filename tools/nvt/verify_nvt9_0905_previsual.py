from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def audit_csv_before_cutoff(path: Path, cutoff: datetime) -> list[dict]:
    violations = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            for field in ("t1", "t2"):
                raw = row.get(field)
                if not raw:
                    continue
                value = datetime.strptime(raw, "%Y.%m.%d %H:%M:%S")
                if value >= cutoff:
                    violations.append({
                        "object_id": row.get("object_id"),
                        "field": field,
                        "value": raw,
                    })
    return violations


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify 09/05 no-lookahead replay before first visual adjudication")
    ap.add_argument("--truth", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--overlay-audit", required=True)
    ap.add_argument("--overlay-csv", required=True)
    ap.add_argument("--base-audit", required=True)
    ap.add_argument("--base-csv", required=True)
    args = ap.parse_args()

    truth = load_json(Path(args.truth))
    summary = load_json(Path(args.summary))
    overlay = load_json(Path(args.overlay_audit))
    base = load_json(Path(args.base_audit))

    cutoff = datetime.fromisoformat(truth["render_contract"]["selection_cutoff_exclusive"])
    if cutoff != datetime.fromisoformat("2026-09-05T00:00:00"):
        raise ValueError(f"unexpected 09/05 cutoff: {cutoff.isoformat()}")
    if summary.get("future_bars_used") is not False:
        raise ValueError("09/05 base used future bars")
    if truth["render_contract"].get("future_bars_used_for_selection") is not False:
        raise ValueError("09/05 truth must forbid future bars for selection")
    if truth["render_contract"].get("extend_selected_reference_geometry_beyond_cutoff") is not True:
        raise ValueError("09/05 selected references must be allowed to project right")

    violations = (
        audit_csv_before_cutoff(Path(args.base_csv), cutoff)
        + audit_csv_before_cutoff(Path(args.overlay_csv), cutoff)
    )
    if violations:
        raise ValueError("09/05 generated anchor at/after cutoff: " + json.dumps(violations, ensure_ascii=False))

    # Carry forward only the generalized D1 outer-support rule.
    d1 = overlay.get("d1_visual_truth") or {}
    if d1.get("status") != "BUILT":
        raise ValueError(f"09/05 D1 approved outer support not built: {d1}")
    resolved = d1.get("resolved_truth") or {}
    if resolved.get("anchor_selection") != "PAIRWISE_OUTERMOST_WICK_ENVELOPE":
        raise ValueError(f"09/05 D1 selector changed: {resolved}")
    if int(resolved.get("formation_wick_breach_count", -1)) != 0:
        raise ValueError(f"09/05 D1 approved TL has formation wick breach: {resolved}")

    expectations = truth.get("transition_expectations") or {}
    if expectations.get("lifecycle_layer") != "POST_SELECTOR_PRE_MAPPING":
        raise ValueError(f"09/05 transition lifecycle layer missing: {expectations}")

    source_selection = base.get("source_selection") or {}
    transition_states = base.get("tl_transition_states") or {}
    transition_warmup_audit = base.get("transition_warmup_audit") or {}
    effective_map = base.get("effective_source_to_display_tfs") or {}
    decisions = base.get("transition_display_decisions") or []

    # H4 must be in the explicit gap between the broken old TL and a future
    # replacement N.  During this gap D1 owns the H4 display.
    h4_expect = expectations.get("H4") or {}
    h4_state = transition_states.get("H4") or {}
    if h4_state.get("state") != h4_expect.get("expected_state"):
        raise ValueError(
            f"09/05 H4 transition state mismatch: expected={h4_expect.get('expected_state')} actual={h4_state}"
        )
    if h4_expect.get("display_owner_tf") != "D1":
        raise ValueError(f"09/05 truth H4 owner is not D1: {h4_expect}")
    if "H4" not in (effective_map.get("D1") or []):
        raise ValueError(f"09/05 H4 display is not inherited from D1: {effective_map}")
    if "H4" in (effective_map.get("H4") or []):
        raise ValueError(f"09/05 H4 native display survived transition: {effective_map}")

    h4_decision = [
        x for x in decisions
        if x.get("display_tf") == "H4"
    ]
    if len(h4_decision) != 1 or h4_decision[0].get("parent_source_tf") != "D1":
        raise ValueError(f"09/05 H4 transition ownership decision missing: {h4_decision}")
    if h4_decision[0].get("state_or_reason") != "TRANSITION_NO_TL":
        raise ValueError(f"09/05 H4 ownership reason mismatch: {h4_decision}")

    d1 = source_selection.get("D1") or []
    if len(d1) != 1:
        raise ValueError(f"09/05 D1 parent family missing for H4 transition: {d1}")
    if d1[0].get("display_roles") != ["TL", "CH"]:
        raise ValueError(f"09/05 D1 parent family must use main TL/CH only: {d1[0]}")
    h4_display = [
        x for x in (base.get("selected_families") or [])
        if x.get("display_tf") == "H4"
    ]
    if len(h4_display) != 1:
        raise ValueError(f"09/05 H4 must contain exactly one D1-owned family: {h4_display}")
    if h4_display[0].get("source_tf") != "D1":
        raise ValueError(f"09/05 H4 display source is not D1: {h4_display[0]}")
    if h4_display[0].get("copied_without_reselection") is not True:
        raise ValueError(f"09/05 D1->H4 geometry was reselected: {h4_display[0]}")
    if h4_display[0].get("geometry_signature") != d1[0].get("geometry_signature"):
        raise ValueError(
            f"09/05 D1/H4 geometry mismatch: d1={d1[0].get('geometry_signature')} "
            f"h4={h4_display[0].get('geometry_signature')}"
        )

    # H1 must have a real ACTIVE/NEW_ACTIVE N.  It is the structural owner
    # used on H1 and copied to M15.
    h1_expect = expectations.get("H1") or {}
    h1_state = transition_states.get("H1") or {}
    if h1_state.get("state") not in set(h1_expect.get("expected_states") or []):
        raise ValueError(
            f"09/05 H1 must be ACTIVE/NEW_ACTIVE/REFERENCE_RETAINED before M15 inheritance: {h1_state}"
        )
    h1 = source_selection.get("H1") or []
    if len(h1) != 1:
        raise ValueError(f"09/05 H1 owner family missing: {h1}")
    fam = h1[0]
    if fam.get("display_roles") != ["TL", "CH"]:
        raise ValueError(f"09/05 H1 owner family must use main TL/CH only: {fam}")

    h1_warmup = transition_warmup_audit.get("H1") or {}
    selection_anchor_floor = h1_warmup.get("selection_anchor_floor")
    if not selection_anchor_floor:
        raise ValueError(f"09/05 H1 transition audit missing selection_anchor_floor: {h1_warmup}")
    if h1_warmup.get("future_bars_used") is not False:
        raise ValueError(f"09/05 H1 transition support used future bars: {h1_warmup}")

    if h1_state.get("state") == "REFERENCE_RETAINED":
        if h1_warmup.get("history_replay_used") is not True:
            raise ValueError(
                f"09/05 H1 REFERENCE_RETAINED lacks chronological history replay evidence: {h1_warmup}"
            )
        if fam.get("generation_role") != "REFERENCE":
            raise ValueError(f"09/05 retained H1 is not REFERENCE generation: {fam}")
        if fam.get("history_replay_retained") is not True:
            raise ValueError(f"09/05 retained H1 lacks replay-retained marker: {fam}")
    else:
        floor_dt = datetime.fromisoformat(selection_anchor_floor)
        for field in ("anchor1_time", "anchor2_time"):
            value = fam.get(field)
            if not value or datetime.fromisoformat(value) < floor_dt:
                raise ValueError(
                    f"09/05 newly-selected H1 anchor predates 600-bar floor: field={field} value={value} floor={selection_anchor_floor}"
                )

    # M15 must never own a native source. It receives the exact H1 geometry.
    m15_expect = expectations.get("M15") or {}
    if m15_expect.get("native_selector_enabled") is not False:
        raise ValueError(f"09/05 truth did not disable M15 native selector: {m15_expect}")
    if "M15" in source_selection and source_selection.get("M15"):
        raise ValueError(f"09/05 M15 native source must be disabled: {source_selection.get('M15')}")
    if "M15" not in set(base.get("native_disabled_source_tfs") or []):
        raise ValueError("09/05 M15 is not marked native-disabled in the display policy")
    if "M15" not in (effective_map.get("H1") or []):
        raise ValueError(f"09/05 M15 display is not inherited from H1: {effective_map}")

    m15_display = [
        x for x in (base.get("selected_families") or [])
        if x.get("display_tf") == "M15"
    ]
    if len(m15_display) != 1:
        raise ValueError(f"09/05 M15 must contain exactly one H1-owned family: {m15_display}")
    copied = m15_display[0]
    if copied.get("source_tf") != "H1":
        raise ValueError(f"09/05 M15 display source is not H1: {copied}")
    if copied.get("copied_without_reselection") is not True:
        raise ValueError(f"09/05 H1->M15 geometry was reselected: {copied}")
    if copied.get("geometry_signature") != h1[0].get("geometry_signature"):
        raise ValueError(
            f"09/05 H1/M15 geometry mismatch: h1={h1[0].get('geometry_signature')} "
            f"m15={copied.get('geometry_signature')}"
        )

    report = {
        "schema": "nvt9-0905-previsual-verification/1.0",
        "audit_id": "ID10IQ200",
        "status": "PASS_0905_PREVISUAL_NO_LOOKAHEAD",
        "cutoff_exclusive": cutoff.isoformat(),
        "d1_truth_id": resolved.get("truth_id"),
        "d1_anchor1": d1.get("anchor1"),
        "d1_anchor2": d1.get("anchor2"),
        "d1_formation_wick_breach_count": resolved.get("formation_wick_breach_count"),
        "m15_native_selector_enabled": False,
        "m15_structural_owner": "H1",
        "m15_display": (
            {
                "source_tf": m15_display[0].get("source_tf"),
                "line_id": m15_display[0].get("line_id"),
                "geometry_signature": m15_display[0].get("geometry_signature"),
                "copied_without_reselection": m15_display[0].get("copied_without_reselection"),
            }
            if m15_display else {"source_tf": "H1", "line_id": None, "state": "NO_LINE_WITH_H1"}
        ),
        "h4_status": {
            "state": h4_state.get("state"),
            "reason_code": h4_state.get("reason_code"),
            "display_owner_tf": "D1",
            "parent_line_id": d1[0].get("line_id"),
            "geometry_signature": h4_display[0].get("geometry_signature"),
            "copied_without_reselection": h4_display[0].get("copied_without_reselection"),
        },
        "h1_status": {
            "state": h1_state.get("state"),
            "reason_code": h1_state.get("reason_code"),
            "line_id": h1[0].get("line_id"),
            "display_reason": h1[0].get("display_reason"),
            "transition_warmup_audit": h1_warmup,
            "history_replay_retained": bool(h1_warmup.get("history_replay_used")),
            "selection_anchor_floor": selection_anchor_floor,
        },
        "date_specific_suppressions_applied": summary.get("suppressed_source_directions"),
        "visual_adjudication_status": "PENDING_USER_0905_SCREENSHOT",
    }
    out = Path(args.summary).parent / "NVT9_0905_PREVISUAL_VERIFY.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
