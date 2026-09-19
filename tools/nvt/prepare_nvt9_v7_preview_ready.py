from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepare NVT9 V7 research preview render readiness.")
    ap.add_argument("--v6-audit", required=True)
    ap.add_argument("--v5-regression", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    v6_path = Path(args.v6_audit)
    v5_path = Path(args.v5_regression)
    v6 = load(v6_path)
    v5 = load(v5_path)

    problems = []
    if v6.get("status") != "PASS_V6_PREVIEW":
        problems.append({"reason": "V6_NOT_PASS", "status": v6.get("status")})
    if v5.get("status") != "PASS_V5":
        problems.append({"reason": "V5_NOT_PASS", "status": v5.get("status")})
    if v6.get("source_snapshot_modified") is not False:
        problems.append({"reason": "V6_SOURCE_SNAPSHOT_SAFETY_NOT_CONFIRMED"})
    if v6.get("production_renderer_modified") is not False:
        problems.append({"reason": "V6_PRODUCTION_RENDERER_SAFETY_NOT_CONFIRMED"})
    if v6.get("nca_draw_writeback") is not False:
        problems.append({"reason": "V6_NCA_DRAW_SAFETY_NOT_CONFIRMED"})

    status = "READY_FOR_V7_MT4_PREVIEW" if not problems else "BLOCKED_V7"
    payload = {
        "schema": "nvt9-v7-preview-ready/0.1",
        "status": status,
        "audit_id": "ID10IQ200",
        "source_v6_audit": str(v6_path),
        "source_v5_regression": str(v5_path),
        "preview_snapshot": v6.get("preview_snapshot"),
        "expected_renderer_rows": v6.get("counts_after", {}),
        "suppressed_rows": v6.get("suppressed_counts", {}),
        "renderer_source": "mt4/NCA_NVT9_Preview_Renderer.mq4",
        "renderer_prefix": "NVT9_PREVIEW__",
        "production_prefix": "NCA_DRAW__",
        "manual_objects_untouched": True,
        "production_objects_untouched": True,
        "remaining_host_action": (
            "Install/compile the isolated NCA_NVT9_Preview_Renderer, then run it once on "
            "USDJPY# D1/H4/H1/M15 and capture screenshots for visual comparison."
        ),
        "problems": problems,
        "production_changed": False,
        "renderer_production_changed": False,
        "nca_draw_writeback": False,
        "trade_authority": False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if status == "READY_FOR_V7_MT4_PREVIEW" else 7


if __name__ == "__main__":
    raise SystemExit(main())
