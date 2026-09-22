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

    # M15 generalized display rule: main TL/CH only.
    m15 = (base.get("source_selection") or {}).get("M15") or []
    if len(m15) != 1 or m15[0].get("display_roles") != ["TL", "CH"]:
        raise ValueError(f"09/05 M15 must keep main TL/CH only: {m15}")

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

    report = {
        "schema": "nvt9-0905-previsual-verification/1.0",
        "audit_id": "ID10IQ200",
        "status": "PASS_0905_PREVISUAL_NO_LOOKAHEAD",
        "cutoff_exclusive": cutoff.isoformat(),
        "d1_truth_id": resolved.get("truth_id"),
        "d1_anchor1": d1.get("anchor1"),
        "d1_anchor2": d1.get("anchor2"),
        "d1_formation_wick_breach_count": resolved.get("formation_wick_breach_count"),
        "m15_line_id": m15[0].get("line_id"),
        "h4_status": (
            {
                "line_id": h4[0].get("line_id"),
                "generation_role": h4[0].get("generation_role"),
                "display_reason": h4[0].get("display_reason"),
                "reference_id": h4[0].get("reference_id"),
            }
            if h4 else {"line_id": None, "generation_role": "NO_LINE_PREVISUAL_ALLOWED"}
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
