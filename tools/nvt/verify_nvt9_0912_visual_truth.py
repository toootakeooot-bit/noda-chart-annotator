from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def in_window(value: datetime, start: str, end: str) -> bool:
    return datetime.fromisoformat(start) <= value <= datetime.fromisoformat(end)


def audit_csv_cutoff(path: Path, cutoff: datetime) -> list[dict]:
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
    ap = argparse.ArgumentParser(description="Verify 09/12 runtime output against user-annotated visual truth")
    ap.add_argument("--visual-truth", required=True)
    ap.add_argument("--overlay-audit", required=True)
    ap.add_argument("--overlay-csv", required=True)
    ap.add_argument("--base-audit", required=True)
    ap.add_argument("--base-csv", required=True)
    args = ap.parse_args()

    truth = load_json(Path(args.visual_truth))
    overlay = load_json(Path(args.overlay_audit))
    base = load_json(Path(args.base_audit))
    render_contract = truth["render_contract"]
    cutoff = datetime.fromisoformat(render_contract["selection_cutoff_exclusive"])
    if render_contract.get("future_bars_used_for_selection") is not False:
        raise ValueError("09/12 visual truth must forbid future bars for structure selection")
    if render_contract.get("extend_selected_reference_geometry_beyond_cutoff") is not True:
        raise ValueError("09/12 visual truth must preserve rightward projection of selected references")

    spec = next(
        x for x in truth["approved_families"]
        if x["truth_id"] == "VT0912-D1-001"
    )
    actual = overlay.get("d1_visual_truth") or {}
    if actual.get("status") != "BUILT":
        raise ValueError(f"D1 visual truth not built: {actual}")

    a1 = datetime.fromisoformat(actual["anchor1"]["time"])
    a2 = datetime.fromisoformat(actual["anchor2"]["time"])
    if not in_window(a1, spec["anchor1"]["window_start"], spec["anchor1"]["window_end"]):
        raise ValueError(f"D1 anchor1 outside approved yellow-circle window: {a1.isoformat()}")
    if not in_window(a2, spec["anchor2"]["window_start"], spec["anchor2"]["window_end"]):
        raise ValueError(f"D1 anchor2 outside approved yellow-circle window: {a2.isoformat()}")
    if actual["anchor1"].get("kind") != "LOW" or actual["anchor2"].get("kind") != "LOW":
        raise ValueError("D1 approved anchors are not LOW/LOW")
    if a2 <= a1:
        raise ValueError("D1 anchor2 is not later than anchor1")

    resolved = actual.get("resolved_truth") or {}
    if resolved.get("anchor_selection") != "PAIRWISE_OUTERMOST_WICK_ENVELOPE":
        raise ValueError(
            "D1 approved selector is not outer wick envelope: "
            + str(resolved.get("anchor_selection"))
        )
    if int(resolved.get("formation_wick_breach_count", -1)) != 0:
        raise ValueError(
            "D1 approved TL has formation wick breach: "
            + str(resolved.get("formation_wick_breach_count"))
        )

    overlay_csv = Path(args.overlay_csv)
    overlay_text = overlay_csv.read_text(encoding="utf-8-sig")
    for oid in (
        "X0912-D1-APPROVED-01-TL",
        "X0912-D1-APPROVED-01-CH",
        "X0912-D1-APPROVED-01-HL",
    ):
        if oid not in overlay_text:
            raise ValueError(f"approved D1 object missing: {oid}")

    expected_suppress = {
        ("H1", "FALLING"),
        ("D1", "RISING"),
    }
    actual_suppress = {
        (x.get("source_tf"), x.get("direction"))
        for x in (base.get("suppressed_source_selections") or [])
    }
    missing_suppress = sorted(expected_suppress - actual_suppress)
    if missing_suppress:
        raise ValueError(f"expected rejected base selections survived: {missing_suppress}")

    # H4 must no longer collapse to NO-LINE merely because CURRENT is empty.
    h4_selection = (base.get("source_selection") or {}).get("H4") or []
    if len(h4_selection) != 1:
        raise ValueError(f"H4 retained reference missing: {h4_selection}")
    h4 = h4_selection[0]
    if h4.get("generation_role") != "PREVIOUS":
        raise ValueError(f"H4 fallback is not PREVIOUS/retained: {h4}")
    if h4.get("display_reason") != "SOURCE_TF_RETAINED_PREVIOUS_FALLBACK":
        raise ValueError(f"H4 retained fallback reason missing: {h4}")
    if h4.get("display_roles") != ["TL", "CH"]:
        raise ValueError(f"H4 retained family must be main TL/CH only: {h4.get('display_roles')}")

    m15_selection = (base.get("source_selection") or {}).get("M15") or []
    if len(m15_selection) != 1 or m15_selection[0].get("display_roles") != ["TL", "CH"]:
        raise ValueError(f"M15 historical family must keep main TL/CH only: {m15_selection}")

    selected = base.get("selected_families") or []
    if not any(x.get("source_tf") == "H4" and x.get("display_tf") == "H4" for x in selected):
        raise ValueError("retained H4 family not displayed on H4")
    if not any(x.get("source_tf") == "H4" and x.get("display_tf") == "D1" for x in selected):
        raise ValueError("retained H4 family not copied to D1")

    overlay_cutoff_violations = audit_csv_cutoff(overlay_csv, cutoff)
    base_cutoff_violations = audit_csv_cutoff(Path(args.base_csv), cutoff)
    if overlay_cutoff_violations or base_cutoff_violations:
        raise ValueError(
            "audit geometry contains post-cutoff anchors: "
            + json.dumps({
                "overlay": overlay_cutoff_violations,
                "base": base_cutoff_violations,
            }, ensure_ascii=False)
        )

    report = {
        "schema": "nvt9-0912-visual-truth-verification/1.0",
        "audit_id": "ID10IQ200",
        "status": "PASS_0912_VISUAL_TRUTH",
        "d1_truth_id": spec["truth_id"],
        "resolved_anchor1": actual["anchor1"],
        "resolved_anchor2": actual["anchor2"],
        "tl_break_time": actual.get("tl_break_time"),
        "lifecycle_status": actual.get("lifecycle_status"),
        "d1_anchor_selection": resolved.get("anchor_selection"),
        "formation_wick_breach_count": resolved.get("formation_wick_breach_count"),
        "formation_wick_contact_count": resolved.get("formation_wick_contact_count"),
        "formation_mean_wick_gap": resolved.get("formation_mean_wick_gap"),
        "suppressed_base_selections": base.get("suppressed_source_selections") or [],
        "h4_retained_reference": {
            "line_id": h4.get("line_id"),
            "generation_role": h4.get("generation_role"),
            "display_reason": h4.get("display_reason"),
            "display_roles": h4.get("display_roles"),
        },
        "m15_display_roles": m15_selection[0].get("display_roles"),
        "post_cutoff_anchor_violations": [],
        "render_contract": render_contract,
    }
    out = Path(args.overlay_audit).parent / "NVT9_0912_VISUAL_TRUTH_VERIFY.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
