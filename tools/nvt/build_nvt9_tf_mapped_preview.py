from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from live_draw.market_input import load_ohlc_csv
from live_draw.normal_run import safe_symbol_filename

ROLES = ("TL", "CH", "TL_ZONE_EDGE", "CH_ZONE_EDGE")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def mt4_datetime(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%Y.%m.%d %H:%M:%S")


def projected_values(s: dict, at: datetime) -> tuple[float, float]:
    t1 = datetime.fromisoformat(s["anchor1_time"])
    t2 = datetime.fromisoformat(s["anchor2_time"])
    p1 = float(s["anchor1_price"])
    p2 = float(s["anchor2_price"])
    sec = (t2 - t1).total_seconds()
    slope = (p2 - p1) / sec
    tl = p1 + slope * (at - t1).total_seconds()
    ch = tl + float(s["ch_offset"])
    return tl, ch


def channel_distance(price: float, tl: float, ch: float) -> float:
    lo, hi = sorted((tl, ch))
    if lo <= price <= hi:
        return 0.0
    return min(abs(price - lo), abs(price - hi))


def line_points(s: dict, role: str) -> tuple[float, float]:
    p1 = float(s["anchor1_price"])
    p2 = float(s["anchor2_price"])
    offset = float(s["ch_offset"])
    width = float(s["zone_width"])
    direction = s["direction"]

    if role == "TL":
        return p1, p2
    if role == "CH":
        return p1 + offset, p2 + offset
    if role == "TL_ZONE_EDGE":
        z = width if direction == "RISING" else -width
        return p1 + z, p2 + z
    if role == "CH_ZONE_EDGE":
        z = -width if direction == "RISING" else width
        return p1 + offset + z, p2 + offset + z
    raise ValueError(role)


def geometry_key(s: dict) -> tuple:
    return (
        s.get("direction"),
        s.get("anchor1_time"),
        round(float(s.get("anchor1_price")), 10),
        s.get("anchor2_time"),
        round(float(s.get("anchor2_price")), 10),
        round(float(s.get("ch_offset")), 10),
        round(float(s.get("zone_width")), 10),
    )


def family_record(s: dict, gen_role: str, display_tf: str, price: float, eval_time: datetime) -> dict:
    tl, ch = projected_values(s, eval_time)
    return {
        "source_tf": s["timeframe"],
        "display_tf": display_tf,
        "line_id": s["line_id"],
        "structure_level": s["structure_level"],
        "generation_role": gen_role.upper(),
        "generation": int(s["generation"]),
        "status": s["status"],
        "direction": s["direction"],
        "anchor1_time": s["anchor1_time"],
        "anchor1_price": float(s["anchor1_price"]),
        "anchor2_time": s["anchor2_time"],
        "anchor2_price": float(s["anchor2_price"]),
        "ch_offset": float(s["ch_offset"]),
        "zone_width": float(s["zone_width"]),
        "projected_tl": tl,
        "projected_ch": ch,
        "current_price": price,
        "distance_to_channel": channel_distance(price, tl, ch),
        "inside_channel": channel_distance(price, tl, ch) == 0.0,
        "_state": s,
    }


def select_families(candidates: list[dict], sources: list[str], near_count: int, context_max: int) -> list[dict]:
    # Exact geometry duplicates are display duplicates; keep the higher source in sources.
    source_rank = {tf: i for i, tf in enumerate(sources)}
    by_geom: dict[tuple, list[dict]] = defaultdict(list)
    for c in candidates:
        by_geom[geometry_key(c["_state"])].append(c)

    deduped = []
    for group in by_geom.values():
        group.sort(key=lambda x: (
            source_rank.get(x["source_tf"], 999),
            0 if x["generation_role"] == "CURRENT" else 1,
            x["distance_to_channel"],
            x["line_id"],
        ))
        chosen = group[0]
        chosen["exact_geometry_duplicate_count"] = len(group) - 1
        deduped.append(chosen)

    ranked = sorted(
        deduped,
        key=lambda x: (
            x["distance_to_channel"],
            0 if x["generation_role"] == "CURRENT" else 1,
            0 if x["structure_level"] == "LARGE_DOW" else 1,
            source_rank.get(x["source_tf"], 999),
            x["line_id"],
        ),
    )

    selected = []
    for c in ranked[:near_count]:
        item = dict(c)
        item["display_reason"] = "NEAR_CURRENT_PRICE"
        item["display_roles"] = list(ROLES)
        selected.append(item)

    # Preserve one farther higher-TF context family only when nearby selection
    # does not already make the broader direction clear.
    if len(sources) > 1 and context_max > 0:
        upper_tf = sources[0]
        near_has_upper = any(x["source_tf"] == upper_tf for x in selected)
        near_directions = {x["direction"] for x in selected}
        direction_unclear = (not near_has_upper) or len(near_directions) > 1

        if direction_unclear:
            existing = {x["line_id"] for x in selected}
            context = [
                x for x in ranked
                if x["source_tf"] == upper_tf
                and x["generation_role"] == "CURRENT"
                and x["line_id"] not in existing
            ]
            context.sort(key=lambda x: (
                0 if x["structure_level"] == "LARGE_DOW" else 1,
                x["distance_to_channel"],
                x["line_id"],
            ))
            for c in context[:context_max]:
                item = dict(c)
                item["display_reason"] = "FAR_HIGHER_TF_DIRECTION_CONTEXT"
                item["display_roles"] = ["TL", "CH"]
                selected.append(item)

    return selected


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build a price-relevant local+parent TF research display preview."
    )
    ap.add_argument("--state", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    state_path = Path(args.state)
    policy_path = Path(args.policy)
    input_dir = Path(args.input_dir)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    state = load_json(state_path)
    policy = load_json(policy_path)
    display_sources = policy.get("display_sources") or {}
    vis = policy.get("visibility_policy") or {}
    near_count = int(vis.get("near_price_family_count", 2))
    context_max = int(vis.get("far_direction_context_max_families", 1))

    if state.get("research_status") != "PASS_DEEP_LIFECYCLE_STATE":
        raise ValueError(f"deep lifecycle state is not PASS: {state.get('research_status')}")

    symbol = state.get("symbol") or policy.get("symbol")
    safe = safe_symbol_filename(symbol)

    latest = {}
    missing = []
    for display_tf in display_sources:
        src = input_dir / f"NVT_{safe}_{display_tf}.csv"
        if not src.exists():
            missing.append(str(src))
            continue
        bars = load_ohlc_csv(src)
        if not bars:
            missing.append(str(src))
            continue
        latest[display_tf] = {
            "time": bars[-1].time,
            "close": float(bars[-1].close),
        }
    if missing:
        raise ValueError(f"missing display timeframe input: {missing}")

    rows = []
    audit_rows = []
    display_counts = Counter()
    candidate_counts = Counter()
    selected_family_counts = Counter()

    slots = state.get("slots") or {}

    for display_tf, sources in display_sources.items():
        eval_time = latest[display_tf]["time"]
        current_price = latest[display_tf]["close"]
        candidates = []

        for _, slot in sorted(slots.items()):
            for gen_role in ("previous", "current"):
                s = slot.get(gen_role)
                if not s or s.get("timeframe") not in sources:
                    continue
                candidates.append(family_record(s, gen_role, display_tf, current_price, eval_time))

        candidate_counts[display_tf] = len(candidates)
        selected = select_families(candidates, list(sources), near_count, context_max)
        selected_family_counts[display_tf] = len(selected)

        for fam in selected:
            s = fam["_state"]
            for role in fam["display_roles"]:
                p1, p2 = line_points(s, role)
                oid = (
                    f"TFMAP__SRC_{fam['source_tf']}__DST_{display_tf}__"
                    f"{s['line_id']}__{role}"
                )
                rows.append([
                    oid, s["symbol"], display_tf, s["structure_level"], role,
                    mt4_datetime(s["anchor1_time"]), f"{p1:.8f}",
                    mt4_datetime(s["anchor2_time"]), f"{p2:.8f}",
                    fam["generation_role"], str(s["generation"]), s["status"], "RAY_RIGHT",
                ])
                display_counts[display_tf] += 1

            audit_rows.append({
                k: v for k, v in fam.items() if k != "_state"
            })

    header = [
        "object_id","symbol","timeframe","structure_level","role",
        "t1","p1","t2","p2","generation_role","generation","status","extent",
    ]
    csv_path = outdir / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv"
    audit_path = outdir / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    payload = {
        "schema": "nvt9-tf-mapped-preview/0.2",
        "status": "PASS_TF_MAPPED_PREVIEW",
        "audit_id": "ID10IQ200",
        "source_state": str(state_path),
        "display_policy": str(policy_path),
        "display_sources": display_sources,
        "latest_display_prices": {
            tf: {"time": x["time"].isoformat(), "close": x["close"]} for tf, x in latest.items()
        },
        "candidate_family_counts": dict(candidate_counts),
        "selected_family_counts": dict(selected_family_counts),
        "display_row_counts": dict(display_counts),
        "selected_families": audit_rows,
        "selection_policy": {
            "near_price_family_count": near_count,
            "far_direction_context_max_families": context_max,
            "fixed_pip_threshold_used": False,
            "atr_threshold_used": False,
            "far_direction_roles": ["TL", "CH"],
        },
        "semantics": {
            "structural_owner_tf": "SOURCE_TF",
            "display_tf": "CHART_TF",
            "h1_h4_nonexact_merge": "NOT_AUTOMATIC",
        },
        "production_changed": False,
        "production_snapshot_changed": False,
        "production_renderer_changed": False,
        "nca_draw_writeback": False,
        "trade_authority": False,
    }
    audit_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": payload["status"],
        "display_sources": display_sources,
        "selected_family_counts": dict(selected_family_counts),
        "display_row_counts": dict(display_counts),
        "csv": str(csv_path),
        "audit": str(audit_path),
        "production_changed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
