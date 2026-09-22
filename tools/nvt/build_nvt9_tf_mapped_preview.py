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

from live_draw.geometry import build_channel_candidates
from live_draw.market_input import load_ohlc_csv
from live_draw.normal_run import safe_symbol_filename
from live_draw.tl_transition import resolve_tl_transition_state
from live_draw.turn_detector import detect_turns

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


def selected_line_hl_evidence(s: dict) -> dict:
    """Return the decision HL persisted with the selected source-TF TL.

    This keeps HL tied to the exact TL anchors that were activated by the
    structural N rule. No independent HL re-selection is allowed here.
    """
    required = (
        "decision_hl_time",
        "decision_hl_price",
        "decision_hl_kind",
        "hl_break_time",
        "hl_break_mode",
    )
    missing = [k for k in required if s.get(k) in (None, "")]
    if missing:
        raise ValueError(
            f"selected TL missing decision-HL evidence: line_id={s.get('line_id')} missing={missing}"
        )
    return {
        "pivot_kind": s["decision_hl_kind"],
        "pivot_time": s["decision_hl_time"],
        "pivot_price": float(s["decision_hl_price"]),
        "selection_rule": "SELECTED_TL_DECISION_HL",
        "line_id": s["line_id"],
        "direction": s["direction"],
        "anchor1_time": s["anchor1_time"],
        "anchor2_time": s["anchor2_time"],
        "hl_break_time": s["hl_break_time"],
        "hl_break_mode": s["hl_break_mode"],
        "always_draw": True,
        "retracement_38_role": "PIVOT_CONFIRMATION_ONLY_NOT_HL",
    }

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


def transition_candidate_state(candidate, symbol: str, timeframe: str) -> dict:
    """Serialize an already-valid N candidate selected by the transition layer."""
    return {
        "line_id": f"TRANS_{timeframe}_{candidate.direction}_{candidate.anchor2.time.strftime('%Y%m%d%H%M')}",
        "symbol": symbol,
        "timeframe": timeframe,
        "structure_level": "LARGE_DOW",
        "generation": 0,
        "status": "ACTIVE",
        "direction": candidate.direction,
        "anchor1_time": candidate.anchor1.time.isoformat(),
        "anchor1_price": float(candidate.anchor1.price),
        "anchor2_time": candidate.anchor2.time.isoformat(),
        "anchor2_price": float(candidate.anchor2.price),
        "ch_offset": float(candidate.ch_offset),
        "zone_width": float(candidate.zone_width),
        "selection_version": "POST_SELECTOR_TL_TRANSITION_V01",
        "decision_hl_time": candidate.decision_hl.time.isoformat(),
        "decision_hl_price": float(candidate.decision_hl.price),
        "decision_hl_kind": candidate.decision_hl.kind,
        "hl_break_time": candidate.hl_break_time.isoformat(),
        "hl_break_mode": candidate.hl_break_mode,
    }


def select_source_families(
    candidates: list[dict],
    source_tf: str,
    per_source: int,
    allowed_generation_roles: tuple[str, ...] = ("CURRENT",),
    display_reason: str = "SOURCE_TF_NEAREST_FAMILY",
    main_roles_only: bool = False,
) -> list[dict]:
    # Selection is made ONCE on the SOURCE timeframe using the source
    # timeframe's own latest closed bar / current price. The chosen geometry
    # is then copied unchanged to every display chart in Plan B.
    by_geom: dict[tuple, list[dict]] = defaultdict(list)
    for c in candidates:
        if c["source_tf"] != source_tf:
            continue
        if c["generation_role"] not in allowed_generation_roles:
            continue
        by_geom[geometry_key(c["_state"])].append(c)

    deduped = []
    for group in by_geom.values():
        group.sort(key=lambda x: (
            x["distance_to_channel"],
            0 if x["structure_level"] == "LARGE_DOW" else 1,
            x["line_id"],
        ))
        chosen = group[0]
        chosen["exact_geometry_duplicate_count"] = len(group) - 1
        deduped.append(chosen)

    ranked = sorted(
        deduped,
        key=lambda x: (
            x["distance_to_channel"],
            0 if x["structure_level"] == "LARGE_DOW" else 1,
            x["line_id"],
        ),
    )
    selected = []
    for c in ranked[:per_source]:
        item = dict(c)
        item["display_reason"] = display_reason
        item["display_roles"] = ["TL", "CH"] if main_roles_only else list(ROLES)
        selected.append(item)
    return selected

def build_revalidated_reference_family(
    reference_manifest: dict,
    source_tf: str,
    bars: list,
    symbol: str,
    current_price: float,
    eval_time: datetime,
    main_roles_only: bool,
) -> list[dict]:
    """Revalidate a frozen reference anchor pair using ONLY supplied bars.

    The frozen manifest contributes identity/anchor expectations only.
    Geometry evidence (confirmed pivots, decision HL, activation, CH offset,
    zone width) is rebuilt from the pre-cutoff bars.  If the exact reference
    anchor pair is not a valid candidate in those bars, no fallback is emitted.
    """
    turns = detect_turns(bars)
    candidates = build_channel_candidates(bars, turns.pivots)
    refs = [
        x for x in (reference_manifest.get("lines") or [])
        if x.get("timeframe") == source_tf
        and x.get("status") in {"ACTIVE", "REFERENCE_RETAINED", "RETIRED"}
    ]
    refs.sort(key=lambda x: (
        0 if x.get("structure_level") == "LARGE_DOW" else 1,
        int(x.get("reference_no", 9999)),
    ))

    matched = []
    for ref in refs:
        ra1t = datetime.fromisoformat(ref["anchor1_time"])
        ra2t = datetime.fromisoformat(ref["anchor2_time"])
        ra1p = float(ref["anchor1_price"])
        ra2p = float(ref["anchor2_price"])
        direction = ref["direction"]

        for c in candidates:
            if c.direction != direction:
                continue
            if c.anchor1.time != ra1t or c.anchor2.time != ra2t:
                continue
            if abs(float(c.anchor1.price) - ra1p) > 1e-9:
                continue
            if abs(float(c.anchor2.price) - ra2p) > 1e-9:
                continue
            # All confirmation/activation evidence comes from the supplied
            # pre-cutoff bar set because build_channel_candidates() ran only
            # on those bars.
            state = {
                "line_id": f"REF0912_{ref['reference_id']}",
                "symbol": symbol,
                "timeframe": source_tf,
                "structure_level": ref["structure_level"],
                "generation": int(ref.get("generation", 0)),
                "status": "REFERENCE_RETAINED",
                "direction": c.direction,
                "anchor1_time": c.anchor1.time.isoformat(),
                "anchor1_price": float(c.anchor1.price),
                "anchor2_time": c.anchor2.time.isoformat(),
                "anchor2_price": float(c.anchor2.price),
                "ch_offset": float(c.ch_offset),
                "zone_width": float(c.zone_width),
                "selection_version": "FROZEN_REFERENCE_ANCHORS_REVALIDATED_PRE_CUTOFF",
                "decision_hl_time": c.decision_hl.time.isoformat(),
                "decision_hl_price": float(c.decision_hl.price),
                "decision_hl_kind": c.decision_hl.kind,
                "hl_break_time": c.hl_break_time.isoformat(),
                "hl_break_mode": c.hl_break_mode,
                "reference_id": ref["reference_id"],
                "reference_anchor_revalidated": True,
                "anchor1_confirmed_by_time": c.anchor1.confirmed_by_time.isoformat(),
                "anchor2_confirmed_by_time": c.anchor2.confirmed_by_time.isoformat(),
                "decision_hl_confirmed_by_time": c.decision_hl.confirmed_by_time.isoformat(),
            }
            fam = family_record(state, "reference", source_tf, current_price, eval_time)
            fam["display_reason"] = "SOURCE_TF_FROZEN_REFERENCE_REVALIDATED"
            fam["display_roles"] = ["TL", "CH"] if main_roles_only else list(ROLES)
            fam["reference_id"] = ref["reference_id"]
            fam["reference_anchor_revalidated"] = True
            matched.append(fam)
            break

    if not matched:
        return []

    matched.sort(key=lambda x: (
        x["distance_to_channel"],
        0 if x["structure_level"] == "LARGE_DOW" else 1,
        x["reference_id"],
    ))
    return [matched[0]]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build a price-relevant local+parent TF research display preview."
    )
    ap.add_argument("--state", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--input-prefix", default="NVT", choices=["NVT", "NORMAL"])
    ap.add_argument("--output-dir", required=True)
    ap.add_argument(
        "--fallback-previous-source-tf",
        action="append",
        default=[],
        choices=["D1", "H4", "H1", "M15"],
        help="Research-only: if CURRENT is absent, select the nearest PREVIOUS family for this source TF.",
    )
    ap.add_argument("--fallback-reference-manifest")
    ap.add_argument(
        "--fallback-reference-source-tf",
        action="append",
        default=[],
        choices=["D1", "H4", "H1", "M15"],
        help="Research-only: if CURRENT/PREVIOUS are absent, revalidate frozen reference anchors using pre-cutoff bars.",
    )
    ap.add_argument(
        "--main-roles-only-source-tf",
        action="append",
        default=[],
        choices=["D1", "H4", "H1", "M15"],
        help="Research-only: draw only TL/CH for this source TF; suppress zone edges.",
    )
    ap.add_argument(
        "--suppress-selected-source-direction",
        action="append",
        default=[],
        help="Research-only selector override in TF:DIRECTION form, e.g. H1:FALLING.",
    )
    ap.add_argument(
        "--allow-empty-source-tf",
        action="append",
        default=[],
        choices=["D1", "H4", "H1", "M15"],
        help="Research-only: allow this source timeframe to have zero selected CURRENT families.",
    )
    args = ap.parse_args()

    state_path = Path(args.state)
    policy_path = Path(args.policy)
    input_dir = Path(args.input_dir)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    allow_empty_source_tfs = set(args.allow_empty_source_tf or [])
    fallback_previous_source_tfs = set(args.fallback_previous_source_tf or [])
    fallback_reference_source_tfs = set(args.fallback_reference_source_tf or [])
    fallback_reference_manifest = (
        load_json(Path(args.fallback_reference_manifest))
        if args.fallback_reference_manifest else {}
    )
    main_roles_only_source_tfs = set(args.main_roles_only_source_tf or [])
    suppress_selected_source_direction = {}
    for item in (args.suppress_selected_source_direction or []):
        if ":" not in item:
            raise ValueError(f"invalid --suppress-selected-source-direction: {item}")
        tf, direction = item.split(":", 1)
        tf = tf.strip().upper()
        direction = direction.strip().upper()
        if tf not in {"D1","H4","H1","M15"} or direction not in {"RISING","FALLING"}:
            raise ValueError(f"invalid --suppress-selected-source-direction: {item}")
        suppress_selected_source_direction[tf] = direction

    state = load_json(state_path)
    policy = load_json(policy_path)
    display_sources = policy.get("display_sources") or {}
    source_to_display = policy.get("source_to_display_tfs") or {}
    native_disabled_source_tfs = set(policy.get("native_disabled_source_tfs") or [])
    transition_state_source_tfs = set(policy.get("transition_state_source_tfs") or [])
    transition_inheritance = policy.get("transition_inheritance") or {}
    vis = policy.get("visibility_policy") or {}
    per_source = int(vis.get("near_price_family_per_source_tf", 1))
    context_max = int(vis.get("far_direction_context_max_families", 0))

    # A disabled source TF may still be a DISPLAY chart, but it must not own
    # structural selection or appear as an input source for another chart.
    invalid_disabled_sources = sorted(tf for tf in native_disabled_source_tfs if tf in source_to_display)
    if invalid_disabled_sources:
        raise ValueError(
            f"native-disabled source TF present in source_to_display_tfs: {invalid_disabled_sources}"
        )
    disabled_leaks = sorted({
        src
        for sources in display_sources.values()
        for src in (sources or [])
        if src in native_disabled_source_tfs
    })
    if disabled_leaks:
        raise ValueError(
            f"native-disabled source TF leaked into display_sources: {disabled_leaks}"
        )

    if state.get("schema") != "nca-live-state/1.0":
        raise ValueError(f"unexpected state schema: {state.get('schema')}")
    research_status = state.get("research_status")
    if research_status is not None and research_status != "PASS_DEEP_LIFECYCLE_STATE":
        raise ValueError(f"research lifecycle state is not PASS: {research_status}")

    symbol = state.get("symbol") or policy.get("symbol")
    safe = safe_symbol_filename(symbol)

    latest = {}
    bars_by_tf = {}
    missing = []
    for display_tf in display_sources:
        src = input_dir / f"{args.input_prefix}_{safe}_{display_tf}.csv"
        if not src.exists():
            missing.append(str(src))
            continue
        bars = load_ohlc_csv(src)
        if not bars:
            missing.append(str(src))
            continue
        bars_by_tf[display_tf] = bars
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
    selected_source_counts: dict[str, Counter] = {}
    source_selection: dict[str, list[dict]] = {}
    hl_candidates: dict[str, dict] = {}
    suppressed_source_selections: list[dict] = []

    slots = state.get("slots") or {}
    if not source_to_display:
        raise ValueError("policy missing source_to_display_tfs")

    # 1) Select the source family on its OWN timeframe.
    for source_tf, display_tfs in source_to_display.items():
        if source_tf not in latest:
            raise ValueError(f"missing latest source market data for {source_tf}")
        eval_time = latest[source_tf]["time"]
        current_price = latest[source_tf]["close"]
        candidates = []
        for _, slot in sorted(slots.items()):
            for gen_role in ("previous", "current"):
                s = slot.get(gen_role)
                if not s or s.get("timeframe") != source_tf:
                    continue
                candidates.append(family_record(s, gen_role, source_tf, current_price, eval_time))

        candidate_counts[source_tf] = sum(
            1 for x in candidates if x["generation_role"] == "CURRENT"
        )
        selected = select_source_families(
            candidates,
            source_tf,
            per_source,
            allowed_generation_roles=("CURRENT",),
            display_reason="SOURCE_TF_NEAREST_FAMILY",
            main_roles_only=(source_tf in main_roles_only_source_tfs),
        )
        if len(selected) < per_source and source_tf in fallback_previous_source_tfs:
            selected = select_source_families(
                candidates,
                source_tf,
                per_source,
                allowed_generation_roles=("PREVIOUS",),
                display_reason="SOURCE_TF_RETAINED_PREVIOUS_FALLBACK",
                main_roles_only=(source_tf in main_roles_only_source_tfs),
            )
        if len(selected) < per_source and source_tf in fallback_reference_source_tfs:
            if not fallback_reference_manifest:
                raise ValueError(
                    f"fallback reference requested for {source_tf} but no manifest was provided"
                )
            selected = build_revalidated_reference_family(
                fallback_reference_manifest,
                source_tf,
                bars_by_tf[source_tf],
                symbol,
                current_price,
                eval_time,
                main_roles_only=(source_tf in main_roles_only_source_tfs),
            )
        if len(selected) < per_source:
            if source_tf in allow_empty_source_tfs and len(selected) == 0:
                source_selection[source_tf] = []
                continue
            raise ValueError(
                f"source selection missing: {source_tf} selected={len(selected)} expected={per_source}"
            )
        suppress_direction = suppress_selected_source_direction.get(source_tf)
        if suppress_direction and selected and selected[0]["direction"] == suppress_direction:
            fam = selected[0]
            suppressed_source_selections.append({
                "source_tf": source_tf,
                "line_id": fam["line_id"],
                "direction": fam["direction"],
                "structure_level": fam["structure_level"],
                "generation": fam["generation"],
                "reason_code": "AUDIT_SUPPRESS_SELECTED_SOURCE_DIRECTION",
            })
            source_selection[source_tf] = []
            continue

        source_selection[source_tf] = selected

    # 2) Post-selector TL lifecycle state.
    #    ACTIVE: selected TL is still valid.
    #    TRANSITION_NO_TL: old TL has broken and no replacement N is active.
    #    NEW_ACTIVE: two same-side pivots + Decision-HL break already establish
    #                a replacement N, even if the persisted selector state lags.
    tl_transition_states = {}
    for source_tf in sorted(transition_state_source_tfs):
        if source_tf not in bars_by_tf:
            raise ValueError(f"transition-state TF missing bars: {source_tf}")
        existing = source_selection.get(source_tf) or []
        existing_state = existing[0]["_state"] if existing else None
        resolved = resolve_tl_transition_state(
            bars_by_tf[source_tf],
            symbol,
            source_tf,
            existing_state,
        )
        tl_transition_states[source_tf] = resolved.to_audit_dict()

        if resolved.state == "TRANSITION_NO_TL":
            source_selection[source_tf] = []
        elif resolved.active_candidate is not None:
            needs_replace = (
                not existing
                or resolved.state == "NEW_ACTIVE"
            )
            if needs_replace:
                state_row = transition_candidate_state(
                    resolved.active_candidate, symbol, source_tf
                )
                fam = family_record(
                    state_row,
                    "current",
                    source_tf,
                    latest[source_tf]["close"],
                    latest[source_tf]["time"],
                )
                fam["display_reason"] = (
                    "TL_TRANSITION_NEW_ACTIVE"
                    if resolved.state == "NEW_ACTIVE"
                    else "TL_TRANSITION_ACTIVE"
                )
                fam["display_roles"] = (
                    ["TL", "CH"]
                    if source_tf in main_roles_only_source_tfs
                    else list(ROLES)
                )
                source_selection[source_tf] = [fam]

    # Rebuild HL evidence only after lifecycle resolution so a broken source
    # cannot keep an HL and a NEW_ACTIVE source owns its own Decision HL.
    hl_candidates = {}
    for source_tf, selected in source_selection.items():
        if not selected:
            continue
        hl_candidates[source_tf] = selected_line_hl_evidence(selected[0]["_state"])

    # 3) Resolve effective display ownership.
    # Base source_to_display_tfs contains native ownership. Transition rules may
    # replace only the DISPLAY owner; geometry is never reselected downstream.
    effective_source_to_display = {
        src: list(dsts) for src, dsts in source_to_display.items()
    }
    transition_display_decisions = []

    for display_tf, rule in transition_inheritance.items():
        parent_tf = rule.get("parent_source_tf")
        when = set(rule.get("when") or [])
        if not parent_tf:
            raise ValueError(f"transition inheritance missing parent_source_tf: {display_tf}")

        apply_rule = False
        reason = None
        if display_tf in native_disabled_source_tfs and "NATIVE_DISABLED" in when:
            apply_rule = True
            reason = "NATIVE_DISABLED"
        else:
            child_state = (tl_transition_states.get(display_tf) or {}).get("state")
            if child_state in when:
                apply_rule = True
                reason = child_state

        if not apply_rule:
            continue

        # Remove native ownership of this display chart from every source,
        # then assign the parent source exactly once.
        for src in list(effective_source_to_display):
            effective_source_to_display[src] = [
                x for x in effective_source_to_display[src] if x != display_tf
            ]
        effective_source_to_display.setdefault(parent_tf, [])
        if display_tf not in effective_source_to_display[parent_tf]:
            effective_source_to_display[parent_tf].append(display_tf)

        transition_display_decisions.append({
            "display_tf": display_tf,
            "state_or_reason": reason,
            "parent_source_tf": parent_tf,
            "suppress_native": bool(rule.get("suppress_native", True)),
            "copied_without_reselection": True,
        })

    # 4) Copy the EXACT selected source geometry to each effective display TF.
    for source_tf, display_tfs in effective_source_to_display.items():
        for fam in source_selection[source_tf]:
            s = fam["_state"]
            geometry_signature = geometry_key(s)
            for display_tf in display_tfs:
                selected_source_counts.setdefault(display_tf, Counter())
                selected_source_counts[display_tf][source_tf] += 1
                selected_family_counts[display_tf] += 1

                for role in fam["display_roles"]:
                    p1, p2 = line_points(s, role)
                    level_code = "L" if s["structure_level"] == "LARGE_DOW" else "M"
                    gen_role_code = (
                        "C" if fam["generation_role"] == "CURRENT"
                        else ("P" if fam["generation_role"] == "PREVIOUS" else "R")
                    )
                    oid = (
                        f"SRC_{source_tf}_DST_{display_tf}_"
                        f"{level_code}_G{s['generation']}_{gen_role_code}_{role}"
                    )
                    rows.append([
                        oid, s["symbol"], display_tf, s["structure_level"], role,
                        mt4_datetime(s["anchor1_time"]), f"{p1:.8f}",
                        mt4_datetime(s["anchor2_time"]), f"{p2:.8f}",
                        fam["generation_role"], str(s["generation"]), s["status"], "RAY_RIGHT",
                    ])
                    display_counts[display_tf] += 1

                audit_rows.append({
                    **{k: v for k, v in fam.items() if k != "_state"},
                    "source_selection_tf": source_tf,
                    "display_tf": display_tf,
                    "geometry_signature": list(geometry_signature),
                    "copied_without_reselection": True,
                })

    # 3) Draw the single decision HL tied to the selected source-TF TL.
    # FALLING TL => LOW HL between the two HIGH anchors.
    # RISING TL  => HIGH HL between the two LOW anchors.
    for source_tf, hl in hl_candidates.items():
        t1 = datetime.fromisoformat(hl["pivot_time"])
        t2 = latest[source_tf]["time"]
        if t2 <= t1:
            from datetime import timedelta
            t2 = t1 + timedelta(seconds=1)
        price = float(hl["pivot_price"])
        side = "HIGH" if hl["pivot_kind"] == "HIGH" else "LOW"
        oid = f"HL_{side}_SRC_{source_tf}_DST_{source_tf}"
        rows.append([
            oid, symbol, source_tf, f"HL_{side}", "HL",
            mt4_datetime(t1.isoformat()), f"{price:.8f}",
            mt4_datetime(t2.isoformat()), f"{price:.8f}",
            "CURRENT", "0", "ACTIVE", "RAY_RIGHT",
        ])
        display_counts[source_tf] += 1

    header = [
        "object_id","symbol","timeframe","structure_level","role",
        "t1","p1","t2","p2","generation_role","generation","status","extent",
    ]
    csv_path = outdir / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv"
    audit_path = outdir / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json"

    # Match Production snapshot encoding: no UTF-8 BOM.
    # MT4 opens this file with FILE_ANSI; a BOM would prefix the first header
    # token and make ReadAndValidateHeader() reject "object_id".
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    payload = {
        "schema": "nvt9-tf-mapped-preview/0.2",
        "status": "PASS_TF_MAPPED_PREVIEW",
        "audit_id": "ID10IQ200",
        "source_state": str(state_path),
        "source_state_mode": (
            "NORMAL_RUN_LIVE_STATE" if args.input_prefix == "NORMAL"
            else "DEEP_NVT_RESEARCH_STATE"
        ),
        "input_prefix": args.input_prefix,
        "display_policy": str(policy_path),
        "display_sources": display_sources,
        "source_to_display_tfs": source_to_display,
        "effective_source_to_display_tfs": effective_source_to_display,
        "native_disabled_source_tfs": sorted(native_disabled_source_tfs),
        "transition_state_source_tfs": sorted(transition_state_source_tfs),
        "tl_transition_states": tl_transition_states,
        "transition_inheritance": transition_inheritance,
        "transition_display_decisions": transition_display_decisions,
        "allow_empty_source_tfs": sorted(allow_empty_source_tfs),
        "fallback_previous_source_tfs": sorted(fallback_previous_source_tfs),
        "fallback_reference_source_tfs": sorted(fallback_reference_source_tfs),
        "fallback_reference_manifest": args.fallback_reference_manifest,
        "main_roles_only_source_tfs": sorted(main_roles_only_source_tfs),
        "suppress_selected_source_direction": suppress_selected_source_direction,
        "suppressed_source_selections": suppressed_source_selections,
        "empty_source_tfs": sorted(tf for tf, fams in source_selection.items() if not fams),
        "hl_candidates": hl_candidates,
        "hl_preview_policy": {
            "status": "PROVISIONAL_VIDEO_COMPARE",
            "always_draw": True,
            "display_scope": "SOURCE_CHART_ONLY",
            "break_logic_applied": False,
            "retracement_38_role": "PIVOT_CONFIRMATION_ONLY_NOT_HL",
            "candidate_rule": "SELECTED_TL_DECISION_HL",
            "semantics": {
                "RISING": "highest confirmed HIGH between LOW1 and LOW2; TL eligible only after close above it",
                "FALLING": "lowest confirmed LOW between HIGH1 and HIGH2; TL eligible only after close below it"
            },
            "hl_is_tied_to_selected_tl": True,
            "break_mode": "CLOSED_BAR_CLOSE_PROVISIONAL"
        },
        "source_selection": {
            tf: [
                {
                    **{k: v for k, v in fam.items() if k != "_state"},
                    "geometry_signature": list(geometry_key(fam["_state"])),
                }
                for fam in fams
            ]
            for tf, fams in source_selection.items()
        },
        "latest_display_prices": {
            tf: {"time": x["time"].isoformat(), "close": x["close"]} for tf, x in latest.items()
        },
        "candidate_family_counts": dict(candidate_counts),
        "selected_family_counts": dict(selected_family_counts),
        "selected_source_counts": {
            tf: dict(counts) for tf, counts in selected_source_counts.items()
        },
        "display_row_counts": dict(display_counts),
        "selected_families": audit_rows,
        "object_name_policy": {
            "renderer_prefix": "NVT9_TFMAP__",
            "max_full_object_name_length": max(
                [len("NVT9_TFMAP__" + row[0]) for row in rows] or [0]
            ),
            "mt4_name_limit_guard": 63,
        },
        "selection_policy": {
            "near_price_family_per_source_tf": per_source,
            "generation_scope": (
                "CURRENT_WITH_EXPLICIT_RETAINED_FALLBACK"
                if (fallback_previous_source_tfs or fallback_reference_source_tfs)
                else "CURRENT_ONLY"
            ),
            "far_direction_context_max_families": context_max,
            "allowed_empty_source_tfs": sorted(allow_empty_source_tfs),
            "fallback_previous_source_tfs": sorted(fallback_previous_source_tfs),
            "fallback_previous_semantics": "USE_RETAINED_PREVIOUS_ONLY_WHEN_CURRENT_ABSENT",
            "fallback_reference_source_tfs": sorted(fallback_reference_source_tfs),
            "fallback_reference_semantics": "REVALIDATE_FROZEN_REFERENCE_ANCHORS_AGAINST_PRE_CUTOFF_CANDIDATES_ONLY",
            "main_roles_only_source_tfs": sorted(main_roles_only_source_tfs),
            "native_disabled_source_tfs": sorted(native_disabled_source_tfs),
            "native_disabled_semantics": "DISPLAY_ONLY_NO_SOURCE_SELECTION",
            "transition_state_layer": "POST_SELECTOR_PRE_MAPPING",
            "transition_states": ["ACTIVE", "TRANSITION_NO_TL", "NEW_ACTIVE"],
            "transition_new_active_rule": "EXISTING_N_STRUCTURE_TWO_ANCHORS_PLUS_DECISION_HL_CLOSED_BAR_BREAK",
            "suppressed_source_directions": suppress_selected_source_direction,
            "suppressed_source_semantics": "REMOVE_SOURCE_AND_ALL_PLAN_B_COPIES_NO_REPLACEMENT",
            "empty_source_semantics": "NO_LINE_NO_SYNTHETIC_FALLBACK",
            "fixed_pip_threshold_used": False,
            "atr_threshold_used": False,
            "far_direction_roles": ["TL", "CH"],
        },
        "semantics": {
            "structural_owner_tf": "SOURCE_TF",
            "display_tf": "CHART_TF",
            "h1_h4_nonexact_merge": "NOT_AUTOMATIC",
            "m15_structural_owner": (
                "H1" if "M15" in native_disabled_source_tfs else "M15"
            ),
            "m15_native_selection": (
                "DISABLED" if "M15" in native_disabled_source_tfs else "ENABLED"
            ),
            "transition_display_ownership": "PARENT_TF_WHEN_CHILD_TRANSITION_NO_TL",
        },
        "production_changed": False,
        "production_snapshot_changed": False,
        "production_renderer_changed": False,
        "nca_draw_writeback": False,
        "trade_authority": False,
    }
    source_presence_problems = []
    for source_tf, display_tfs in effective_source_to_display.items():
        for display_tf in display_tfs:
            counts = selected_source_counts.get(display_tf, Counter())
            if counts.get(source_tf, 0) < per_source:
                if source_tf in allow_empty_source_tfs and not source_selection.get(source_tf):
                    continue
                if any(x["source_tf"] == source_tf for x in suppressed_source_selections):
                    continue
                source_presence_problems.append({
                    "display_tf": display_tf,
                    "missing_source_tf": source_tf,
                    "reason": "PLAN_B_ASSIGNED_SOURCE_NOT_COPIED",
                })
    payload["source_presence_problems"] = source_presence_problems
    if source_presence_problems:
        payload["status"] = "FAIL_PLAN_B_SOURCE_PRESENCE"

    audit_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if source_presence_problems:
        raise ValueError(f"Plan B source presence failure: {source_presence_problems}")

    if payload["object_name_policy"]["max_full_object_name_length"] > payload["object_name_policy"]["mt4_name_limit_guard"]:
        raise ValueError(
            "TFMap MT4 object name exceeds 63 characters: "
            f"{payload['object_name_policy']['max_full_object_name_length']}"
        )

    print(json.dumps({
        "status": payload["status"],
        "display_sources": display_sources,
        "effective_source_to_display_tfs": effective_source_to_display,
        "tl_transition_states": tl_transition_states,
        "selected_family_counts": dict(selected_family_counts),
        "selected_source_counts": {
            tf: dict(counts) for tf, counts in selected_source_counts.items()
        },
        "display_row_counts": dict(display_counts),
        "csv": str(csv_path),
        "audit": str(audit_path),
        "production_changed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
