from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def load_rule(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def decision(row: dict, rule: dict) -> tuple[str, str]:
    scope = rule.get("scope", {})
    symbol = scope.get("symbol")
    tfs = set(scope.get("timeframes", []))
    if symbol and row.get("symbol") != symbol:
        return "DRAW", "OUT_OF_SCOPE_PASS_THROUGH"
    if tfs and row.get("timeframe") not in tfs:
        return "DRAW", "OUT_OF_SCOPE_PASS_THROUGH"

    for item in rule.get("policy", []):
        if row.get("generation_role") != item.get("generation_role"):
            continue
        roles = set(item.get("roles", []))
        if roles and row.get("role") not in roles:
            continue
        return item.get("visibility", "DRAW"), item.get("reason", "RULE_MATCH")
    return "DRAW", "NO_RULE_MATCH_PASS_THROUGH"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--rule", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument(
        "--allow-blocked-rule",
        action="store_true",
        help="Explicit research override for a rule whose manifest says it is blocked.",
    )
    args = ap.parse_args()

    snapshot = Path(args.snapshot)
    rule_path = Path(args.rule)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    rule = load_rule(rule_path)
    rule_status = str(rule.get("status", ""))
    if "BLOCKED" in rule_status and not args.allow_blocked_rule:
        print(json.dumps({
            "status": "BLOCKED_BY_RULE_MANIFEST",
            "rule_status": rule_status,
            "rule": str(rule_path),
            "reason": rule.get("block_reason"),
            "production_changed": False,
        }, ensure_ascii=False, indent=2))
        return 8

    with snapshot.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = list(reader.fieldnames or [])

    kept = []
    decisions = []
    before = Counter()
    after = Counter()
    suppressed = Counter()

    for row in rows:
        tf = row.get("timeframe", "")
        before[tf] += 1
        vis, reason = decision(row, rule)
        decisions.append({
            "object_id": row.get("object_id"),
            "symbol": row.get("symbol"),
            "timeframe": tf,
            "structure_level": row.get("structure_level"),
            "generation_role": row.get("generation_role"),
            "role": row.get("role"),
            "visibility": vis,
            "reason": reason,
        })
        if vis == "SUPPRESSED":
            suppressed[tf] += 1
            continue
        kept.append(row)
        after[tf] += 1

    stem = snapshot.stem
    preview = outdir / f"{stem}_VIS_0919_H1_V01.csv"
    audit = outdir / f"{stem}_VIS_0919_H1_V01_audit.json"

    with preview.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(kept)

    payload = {
        "schema": "nvt9-visibility-preview-audit/0.1",
        "status": "PASS",
        "source_snapshot": str(snapshot),
        "rule": str(rule_path),
        "source_snapshot_modified": False,
        "production_renderer_modified": False,
        "nca_draw_writeback": False,
        "counts_before": dict(before),
        "counts_after": dict(after),
        "suppressed_counts": dict(suppressed),
        "decisions": decisions,
        "preview_snapshot": str(preview),
    }
    audit.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": "PASS",
        "counts_before": dict(before),
        "counts_after": dict(after),
        "suppressed_counts": dict(suppressed),
        "preview": str(preview),
        "audit": str(audit),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
