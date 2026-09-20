from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate NVT9 Plan B display mapping against frozen user contract.")
    ap.add_argument("--contract", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    contract = load(Path(args.contract))
    policy = load(Path(args.policy))

    expected_source = contract["source_to_display_tfs"]
    expected_chart = contract["equivalent_chart_sources"]
    actual_source = policy.get("source_to_display_tfs")
    actual_chart = policy.get("display_sources")

    problems = []
    if policy.get("plan") != "B":
        problems.append({"reason": "PLAN_NOT_B", "actual": policy.get("plan")})
    if actual_source != expected_source:
        problems.append({
            "reason": "SOURCE_TO_DISPLAY_DIRECTION_MISMATCH",
            "expected": expected_source,
            "actual": actual_source,
        })
    if actual_chart != expected_chart:
        problems.append({
            "reason": "CHART_SOURCE_MAPPING_MISMATCH",
            "expected": expected_chart,
            "actual": actual_chart,
        })

    # Explicitly reject the previously implemented inverse pattern.
    inverse = contract.get("forbidden_inverse_example") or {}
    if actual_chart == inverse:
        problems.append({"reason": "FORBIDDEN_INVERSE_MAPPING_DETECTED"})

    status = "PASS_PLAN_B_CONTRACT" if not problems else "FAIL_PLAN_B_CONTRACT"
    payload = {
        "schema": "nvt9-plan-b-contract-audit/1.0",
        "status": status,
        "audit_id": contract.get("audit_id"),
        "canonical_direction": contract.get("canonical_direction"),
        "expected_source_to_display_tfs": expected_source,
        "actual_source_to_display_tfs": actual_source,
        "expected_chart_sources": expected_chart,
        "actual_chart_sources": actual_chart,
        "problem_count": len(problems),
        "problems": problems,
        "production_changed": False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if status == "PASS_PLAN_B_CONTRACT" else 9


if __name__ == "__main__":
    raise SystemExit(main())
