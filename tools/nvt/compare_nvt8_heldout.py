from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from live_draw.market_input import load_ohlc_csv
from live_draw.normal_run import rebuild_timeframe_from_bars
from nvt.structure_semantics import default_visibility, evaluate_rising_hierarchy


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_check(report: dict, name: str) -> dict | None:
    for item in report.get("checks") or []:
        if item.get("name") == name:
            return item
    return None


def add_subcheck(rows: list[dict], name: str, passed: bool, detail: str, evidence=None) -> None:
    row = {"name": name, "pass": bool(passed), "detail": detail}
    if evidence is not None:
        row["evidence"] = evidence
    rows.append(row)


def selected_candidate(tf: dict, key_name: str) -> dict | None:
    cid = tf.get(key_name)
    if not cid:
        return None
    for c in tf.get("recent_candidates_since_2026_08_20") or []:
        if c.get("candidate_id") == cid:
            return c
    return None


def line_state_rows(state: dict, symbol: str, timeframe: str) -> list[dict]:
    rows = []
    for key, slot in sorted((state.get("slots") or {}).items()):
        if not key.startswith(f"{symbol}|{timeframe}|"):
            continue
        for generation_role in ("previous", "current"):
            item = slot.get(generation_role)
            if not item:
                continue
            rows.append({
                "slot": key,
                "generation_role": generation_role.upper(),
                "line_id": item.get("line_id"),
                "structure_level": item.get("structure_level"),
                "direction": item.get("direction"),
                "anchor1_time": item.get("anchor1_time"),
                "anchor1_price": item.get("anchor1_price"),
                "anchor2_time": item.get("anchor2_time"),
                "anchor2_price": item.get("anchor2_price"),
                "ch_offset": item.get("ch_offset"),
                "zone_width": item.get("zone_width"),
                "status": item.get("status"),
            })
    return rows


def score_event(event_id: str, subchecks: list[dict], failure_layer: str | None = None) -> dict:
    failures = [x["name"] for x in subchecks if not x["pass"]]
    return {
        "event_id": event_id,
        "status": "PASS" if not failures else "FAIL",
        "failure_layer": None if not failures else failure_layer,
        "subchecks": subchecks,
        "failure_checks": failures,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Strict NVT8 held-out comparison. No tuning, no Production writeback.")
    ap.add_argument("--registry", required=True)
    ap.add_argument("--replay", required=True)
    ap.add_argument("--nvt7-regression", required=True)
    ap.add_argument("--preflight", required=True)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    registry = load_json(args.registry)
    replay = load_json(args.replay)
    nvt7 = load_json(args.nvt7_regression)
    preflight = load_json(args.preflight)

    if registry.get("status") != "FROZEN_AFTER_HELD_OUT_REVIEW":
        raise ValueError("teacher event registry is not frozen")
    if replay.get("status") != "REPLAY_BUNDLE_READY_FOR_HELDOUT_COMPARISON":
        raise ValueError("strict replay bundle is not ready")
    if replay.get("source_id") != registry.get("source_id"):
        raise ValueError("source_id mismatch")
    if replay.get("frozen_algorithm_paths_unchanged") is not True:
        raise ValueError("frozen algorithm paths changed after inspection lock")
    if replay.get("stale_or_missing"):
        raise ValueError("replay has stale/missing timeframe data")
    if nvt7.get("status") != "PASS" or nvt7.get("held_out_validation_ready") is not True:
        raise ValueError("NVT7 frozen-scope regression is not held-out ready")
    if preflight.get("strict_nvt8_can_start") is not True:
        raise ValueError("strict NVT8 preflight is not READY")

    symbol = replay.get("broker_symbol")
    cutoff = datetime.fromisoformat(replay.get("requested_cutoff_broker_time"))
    input_dir = Path(args.input_dir)
    h1_csv = input_dir / f"NVT_{symbol}_H1.csv"
    if not h1_csv.exists():
        raise FileNotFoundError(h1_csv)

    h1_bars = [b for b in load_ohlc_csv(h1_csv) if b.time <= cutoff]
    state, lifecycle_audit = rebuild_timeframe_from_bars(h1_bars, symbol, "H1")
    state_rows = line_state_rows(state, symbol, "H1")

    h1 = replay["timeframes"]["H1"]
    large = selected_candidate(h1, "selected_large_candidate_id")
    mid = selected_candidate(h1, "selected_mid_candidate_id")

    transient_check = find_check(nvt7, "transient_is_filter_not_market_state")
    no_delete_check = find_check(nvt7, "no_default_reference_delete_rule_preserved")

    results = []

    # TE_01: broad major rising structural line retained/drawable.
    s = []
    add_subcheck(
        s, "selected_large_present",
        large is not None,
        "Frozen selector must provide an H1 LARGE candidate at the held-out cutoff.",
        h1.get("selected_large_candidate_id"),
    )
    add_subcheck(
        s, "large_role_drawable",
        default_visibility("LARGE_DOW_TL") == "DRAW",
        "Frozen NVT7.1 semantics must keep LARGE_DOW_TL drawable by default.",
    )
    add_subcheck(
        s, "selected_large_rising_unbroken",
        bool(large) and large.get("direction") == "RISING" and large.get("unbroken_close") is True,
        "Teacher-held-out major support is rising and still structurally usable at the frozen cutoff.",
        None if not large else {
            "candidate_id": large.get("candidate_id"),
            "direction": large.get("direction"),
            "unbroken_close": large.get("unbroken_close"),
            "anchor1": large.get("anchor1"),
            "anchor2": large.get("anchor2"),
        },
    )
    add_subcheck(
        s, "reference_not_newest_only_deleted",
        bool(no_delete_check) and no_delete_check.get("pass") is True,
        "Frozen NVT7 lifecycle contract must preserve useful references from newest-only deletion.",
        no_delete_check,
    )
    results.append(score_event("NVT8_TE_01", s, "SELECTOR_MATCH"))

    # TE_02: channel boundary exists with the selected major structure and is drawable in snapshot semantics.
    s = []
    add_subcheck(
        s, "selected_large_channel_present",
        bool(large) and large.get("ch_anchor") is not None and int(large.get("ch_contacts") or 0) > 0,
        "Selected H1 LARGE candidate must carry a channel boundary with actual CH contacts.",
        None if not large else {
            "candidate_id": large.get("candidate_id"),
            "ch_anchor": large.get("ch_anchor"),
            "ch_contacts": large.get("ch_contacts"),
            "ch_offset": large.get("ch_offset"),
        },
    )
    large_state_rows = [x for x in state_rows if x.get("structure_level") == "LARGE"]
    add_subcheck(
        s, "large_lifecycle_state_exists",
        len(large_state_rows) > 0,
        "Full-history rebuild must retain an H1 LARGE lifecycle state at the frozen cutoff.",
        large_state_rows,
    )
    add_subcheck(
        s, "channel_geometry_finite",
        all(math.isfinite(float(x["ch_offset"])) for x in large_state_rows) if large_state_rows else False,
        "Retained/current LARGE lifecycle states must carry finite CH offsets; snapshot semantics render CH for current/previous states.",
    )
    results.append(score_event("NVT8_TE_02", s, "LIFECYCLE_RETENTION"))

    # TE_03: thin aqua edit is transient observation only.
    s = []
    add_subcheck(
        s, "edit_transient_filter_frozen",
        bool(transient_check) and transient_check.get("pass") is True,
        "Frozen NVT7 must classify EDIT_TRANSIENT as an observation filter, not a stable market-time state.",
        transient_check,
    )
    results.append(score_event("NVT8_TE_03", s, "LIFECYCLE_TRANSIENT_FILTER"))

    # TE_04: local rising can coexist with parent/reference structure and does not auto-promote parent.
    s = []
    semantic = evaluate_rising_hierarchy(
        small_dow_high_broken=True,
        active_large_dow_high_broken=False,
    )
    add_subcheck(
        s, "local_rise_parent_not_promoted",
        semantic.state == "SMALL_DOW_RISING_PARENT_NOT_PROMOTED"
        and semantic.large_dow_promoted is False
        and semantic.next_major_resistance == "ACTIVE_LARGE_DOW_HIGH",
        "Frozen NVT7.1 hierarchy must separate a local rise from parent large-Dow promotion.",
        semantic.to_dict(),
    )
    directions = sorted({x.get("direction") for x in state_rows if x.get("direction")})
    add_subcheck(
        s, "h1_reference_coexistence_at_cutoff",
        len(state_rows) >= 2,
        "Held-out cutoff full-history rebuild must preserve more than one H1 structural line state so local/parent visibility can coexist.",
        {"directions": directions, "states": state_rows},
    )
    add_subcheck(
        s, "no_newest_only_reference_delete",
        bool(no_delete_check) and no_delete_check.get("pass") is True,
        "Parent/reference visibility must not be deleted solely because a newer local structure exists.",
        no_delete_check,
    )
    results.append(score_event("NVT8_TE_04", s, "LIFECYCLE_RETENTION"))

    failures = [r["event_id"] for r in results if r["status"] == "FAIL"]
    strict_status = "PASS_STRICT_NVT8" if not failures else "FAIL_STRICT_NVT8"

    report = {
        "schema": "nvt8-held-out-comparison/1.0",
        "status": strict_status,
        "phase": "NVT8_STRICT_HELD_OUT_COMPARISON",
        "source_id": registry.get("source_id"),
        "source_filename": registry.get("source_filename"),
        "evidence_class": registry.get("evidence_class"),
        "teacher_event_registry_frozen": registry.get("teacher_event_registry_frozen") is True,
        "rule_tuning_after_teacher_review_allowed": False,
        "frozen_algorithm_paths_unchanged": replay.get("frozen_algorithm_paths_unchanged") is True,
        "closed_bar_policy": replay.get("closed_bar_policy"),
        "requested_cutoff_broker_time": replay.get("requested_cutoff_broker_time"),
        "teacher_scored_event_count": len(results),
        "teacher_event_results": results,
        "failure_event_ids": failures,
        "all_scored_events_pass": not failures,
        "h1_lifecycle_rebuild": {
            "audit": lifecycle_audit,
            "final_state_rows": state_rows,
        },
        "interpretation": (
            "PASS_STRICT_NVT8 means all four frozen held-out teacher assertions matched at their declared scope "
            "without post-inspection tuning. FAIL_STRICT_NVT8 records the mismatch as held-out evidence and must "
            "not be patched and rerun against this same source as though it were still held-out."
        ),
        "strict_nvt8_satisfied": not failures,
        "nvt9_promotion_review_ready": not failures,
        "production_promotion_ready": False,
        "production_writeback": False,
        "normal_run_modified": False,
        "mt4_object_writeback": False,
        "trade_authority": False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": strict_status,
        "teacher_scored_event_count": len(results),
        "failure_event_ids": failures,
        "strict_nvt8_satisfied": report["strict_nvt8_satisfied"],
        "nvt9_promotion_review_ready": report["nvt9_promotion_review_ready"],
        "output": str(out),
        "production_writeback": False,
    }, ensure_ascii=False, indent=2))

    return 0 if not failures else 4


if __name__ == "__main__":
    raise SystemExit(main())
