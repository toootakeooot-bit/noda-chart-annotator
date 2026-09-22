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

    # M15 structural ownership is delegated to H1.
    # M15 must not select its own native family.  If H1 has a selected family,
    # that exact geometry must be copied to the M15 display without reselection.
    source_selection = base.get("source_selection") or {}
    if "M15" in source_selection and source_selection.get("M15"):
        raise ValueError(f"09/05 M15 native source must be disabled: {source_selection.get('M15')}")
    if "M15" not in set(base.get("native_disabled_source_tfs") or []):
        raise ValueError("09/05 M15 is not marked native-disabled in the display policy")

    # H4 is intentionally unresolved before first 09/05 screenshot:
    # CURRENT/PREVIOUS/revalidated REFERENCE are all acceptable, and NO-LINE is
    # acceptable only if every pre-cutoff recovery route is absent.
    h4 = (base.get("source_selection") or {}).get("H4") or []
    if h4:
        fam = h4[0]
        if fam.get("generation_role") not in {"CURRENT", "PREVIOUS", "REFERENCE"}:
            raise ValueError(f"09/05 H4 has unsupported generation role: {fam}")
        if fam.get("generation_role") == "REFERENCE" and fam.get("reference_anchor_revalidated") is not True:
            raise ValueError(f"09/05 H4 frozen reference was not revalidated: {fam}")
        if fam.get("display_roles") != ["TL", "CH"]:
            raise ValueError(f"09/05 H4 must keep main TL/CH only: {fam}")

    h1 = source_selection.get("H1") or []
    if h1:
        fam = h1[0]
        if fam.get("generation_role") not in {"CURRENT", "PREVIOUS", "REFERENCE"}:
            raise ValueError(f"09/05 H1 has unsupported generation role: {fam}")
        if fam.get("generation_role") == "REFERENCE" and fam.get("reference_anchor_revalidated") is not True:
            raise ValueError(f"09/05 H1 frozen reference was not revalidated: {fam}")
        if fam.get("display_roles") != ["TL", "CH"]:
            raise ValueError(f"09/05 H1 owner family must use main TL/CH only: {fam}")

    m15_display = [
        x for x in (base.get("selected_families") or [])
        if x.get("display_tf") == "M15"
    ]
    if h1:
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
    elif m15_display:
        raise ValueError(f"09/05 M15 has geometry while H1 is NO-LINE: {m15_display}")

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
        "h4_status": (
            {
                "line_id": h4[0].get("line_id"),
                "generation_role": h4[0].get("generation_role"),
                "display_reason": h4[0].get("display_reason"),
                "reference_id": h4[0].get("reference_id"),
            }
            if h4 else {"line_id": None, "generation_role": "NO_LINE_PREVISUAL_ALLOWED"}
        ),
        "h1_status": (
            {
                "line_id": h1[0].get("line_id"),
                "generation_role": h1[0].get("generation_role"),
                "display_reason": h1[0].get("display_reason"),
                "reference_id": h1[0].get("reference_id"),
            }
            if h1 else {"line_id": None, "generation_role": "NO_LINE_PREVISUAL_ALLOWED"}
        ),
        "date_specific_suppressions_applied": summary.get("suppressed_source_directions"),
        "visual_adjudication_status": "PENDING_USER_0905_SCREENSHOT",
    }
    out = Path(args.summary).parent / "NVT9_0905_PREVISUAL_VERIFY.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
