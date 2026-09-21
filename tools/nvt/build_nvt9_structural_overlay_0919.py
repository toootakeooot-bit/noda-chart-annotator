from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from live_draw.market_input import load_ohlc_csv
from live_draw.normal_run import safe_symbol_filename
from live_draw.turn_detector import detect_turns

CUTOFF = datetime.fromisoformat("2026-09-19T00:00:00")


def mt4_time(value: datetime) -> str:
    return value.strftime("%Y.%m.%d %H:%M:%S")


def slope_per_second(t1: datetime, p1: float, t2: datetime, p2: float) -> float:
    sec = (t2 - t1).total_seconds()
    if sec <= 0:
        raise ValueError("anchor2 must be later than anchor1")
    return (float(p2) - float(p1)) / sec


def line_value(at: datetime, t1: datetime, p1: float, slope: float, offset: float = 0.0) -> float:
    return float(p1) + slope * (at - t1).total_seconds() + float(offset)


def median_bar_range(bars) -> float:
    vals = [max(0.0, float(b.high) - float(b.low)) for b in bars]
    vals = [x for x in vals if x > 0]
    return statistics.median(vals) if vals else 0.0


@dataclass
class ContinuationCandidate:
    anchor1: object
    anchor2: object
    decision_hl: object
    slope: float
    tl_contacts: int
    duration_days: float
    unbroken_close: bool
    hl_break_time: datetime | None
    ch_anchor: object
    ch_offset: float
    tolerance: float

    @property
    def status(self) -> str:
        return "ACTIVE_CONFIRMED" if self.hl_break_time is not None else "REFERENCE_PENDING_HL_BREAK"

    @property
    def id_key(self) -> str:
        return f"D1_CONT:{self.anchor1.time.isoformat()}:{self.anchor2.time.isoformat()}"


def build_d1_continuation(bars, pivots) -> ContinuationCandidate | None:
    lows = [p for p in pivots if p.kind == "LOW"]
    highs = [p for p in pivots if p.kind == "HIGH"]
    if len(lows) < 2 or not highs:
        return None

    tol = max(median_bar_range(bars) * 0.28, 1e-8)
    # D1 broad continuation must not be restricted to only the last few lows.
    # The visual reference can legitimately use an older major pullback low as
    # anchor2 while the newer local sequence develops above it.
    candidates: list[ContinuationCandidate] = []

    for i, a in enumerate(lows[:-1]):
        for b in lows[i + 1:]:
            if b.price <= a.price:
                continue
            between = [h for h in highs if a.time < h.time < b.time]
            if not between:
                continue

            decision_hl = max(between, key=lambda p: (p.price, p.time))
            slope = slope_per_second(a.time, a.price, b.time, b.price)

            # A structural support must remain below closed-bar price for the
            # whole life of the candidate, not only after anchor2.
            broken = False
            for bar in bars:
                if bar.time < a.time:
                    continue
                if bar.close < line_value(bar.time, a.time, a.price, slope) - tol:
                    broken = True
                    break
            if broken:
                continue

            contacts = 0
            for p in lows:
                if p.time < a.time:
                    continue
                if abs(p.price - line_value(p.time, a.time, a.price, slope)) <= tol:
                    contacts += 1

            hl_break_time = None
            for bar in bars:
                if bar.time <= b.time:
                    continue
                if bar.close > decision_hl.price:
                    hl_break_time = bar.time
                    break

            high_pool = [h for h in highs if h.time >= a.time]
            if not high_pool:
                continue
            residuals = [
                (h.price - line_value(h.time, a.time, a.price, slope), h)
                for h in high_pool
            ]
            residuals = [(off, h) for off, h in residuals if off > 0]
            if not residuals:
                continue
            ch_offset, ch_anchor = max(residuals, key=lambda x: (x[0], x[1].time))

            candidates.append(
                ContinuationCandidate(
                    anchor1=a,
                    anchor2=b,
                    decision_hl=decision_hl,
                    slope=slope,
                    tl_contacts=contacts,
                    duration_days=(b.time - a.time).total_seconds() / 86400.0,
                    unbroken_close=True,
                    hl_break_time=hl_break_time,
                    ch_anchor=ch_anchor,
                    ch_offset=ch_offset,
                    tolerance=tol,
                )
            )

    if not candidates:
        return None

    # Prefer a still-pending support reference when available: this is the
    # structure hidden by the production new-direction HL gate.
    #
    # Visual review rejected the old "longest duration first" policy because
    # it can select an obsolete shallow line far below the active D1 support.
    # A continuation-support line must be broad enough to be structural, but
    # among broad unbroken candidates the tightest valid support at the cutoff
    # is preferred. This selects the highest line still supporting closes.
    pending = [c for c in candidates if c.hl_break_time is None]
    pool = pending if pending else candidates

    broad = [c for c in pool if c.duration_days >= 120.0]
    if broad:
        pool = broad

    cutoff_time = bars[-1].time
    cutoff_close = float(bars[-1].close)

    def support_rank(c: ContinuationCandidate):
        projected = line_value(cutoff_time, c.anchor1.time, c.anchor1.price, c.slope)
        support_gap = cutoff_close - projected
        # Unbroken-close gating above means a small negative value may only be
        # within tolerance. Clamp it so tolerance noise cannot win the rank.
        effective_gap = max(0.0, support_gap)
        return (
            -effective_gap,
            c.tl_contacts,
            c.duration_days,
            c.anchor2.time,
            -abs(c.slope),
        )

    return max(pool, key=support_rank)


def build_h1_native_continuation(bars, pivots) -> ContinuationCandidate | None:
    """Build a native H1 rising TL/CH/Decision-HL family.

    This deliberately does not reuse a mapped M15 line.  It uses H1-confirmed
    pivots, prefers a recent structural pullback anchor2, and requires the
    support line to remain unbroken by closed H1 bars.
    """
    lows = [p for p in pivots if p.kind == "LOW"]
    highs = [p for p in pivots if p.kind == "HIGH"]
    if len(lows) < 2 or not highs:
        return None

    tol = max(median_bar_range(bars) * 0.28, 1e-8)
    recent_anchor2_times = {p.time for p in lows[-8:]}
    candidates: list[ContinuationCandidate] = []

    for i, a in enumerate(lows[:-1]):
        for b in lows[i + 1:]:
            if b.time not in recent_anchor2_times:
                continue
            duration_days = (b.time - a.time).total_seconds() / 86400.0
            if duration_days < 2.0:
                continue
            if b.price <= a.price:
                continue

            between = [h for h in highs if a.time < h.time < b.time]
            if not between:
                continue
            decision_hl = max(between, key=lambda p: (p.price, p.time))
            slope = slope_per_second(a.time, a.price, b.time, b.price)

            broken = False
            for bar in bars:
                if bar.time < a.time:
                    continue
                if bar.close < line_value(bar.time, a.time, a.price, slope) - tol:
                    broken = True
                    break
            if broken:
                continue

            contacts = 0
            for p in lows:
                if p.time < a.time:
                    continue
                if abs(p.price - line_value(p.time, a.time, a.price, slope)) <= tol:
                    contacts += 1

            hl_break_time = None
            for bar in bars:
                if bar.time <= b.time:
                    continue
                if bar.close > decision_hl.price:
                    hl_break_time = bar.time
                    break

            # Base CH belongs to the structure that existed by anchor2.
            # Later highs are reserved for Updated-CH adjudication.
            residuals = [
                (h.price - line_value(h.time, a.time, a.price, slope), h)
                for h in between
            ]
            residuals = [(off, h) for off, h in residuals if off > 0]
            if not residuals:
                continue
            ch_offset, ch_anchor = max(residuals, key=lambda x: (x[0], x[1].time))

            candidates.append(
                ContinuationCandidate(
                    anchor1=a,
                    anchor2=b,
                    decision_hl=decision_hl,
                    slope=slope,
                    tl_contacts=contacts,
                    duration_days=duration_days,
                    unbroken_close=True,
                    hl_break_time=hl_break_time,
                    ch_anchor=ch_anchor,
                    ch_offset=ch_offset,
                    tolerance=tol,
                )
            )

    if not candidates:
        return None

    cutoff_time = bars[-1].time
    cutoff_close = float(bars[-1].close)

    # Prefer the newest meaningful H1 pullback structure first.  Within the
    # same anchor2 epoch, prefer the tightest unbroken support and more contacts.
    def rank(c: ContinuationCandidate):
        projected = line_value(cutoff_time, c.anchor1.time, c.anchor1.price, c.slope)
        gap = max(0.0, cutoff_close - projected)
        return (
            c.anchor2.time,
            -gap,
            c.tl_contacts,
            c.duration_days,
        )

    return max(candidates, key=rank)


@dataclass
class WeightedResidual:
    value: float
    weight: float
    bar_index: int
    kind: str


def weighted_quantile(points: list[WeightedResidual], q: float) -> float:
    ordered = sorted(points, key=lambda p: p.value)
    total = sum(p.weight for p in ordered)
    if total <= 0:
        return ordered[len(ordered) // 2].value
    target = total * q
    acc = 0.0
    for p in ordered:
        acc += p.weight
        if acc >= target:
            return p.value
    return ordered[-1].value


def cluster_reaction_zones(bars, *, base_t1, base_p1, base_slope, max_zones: int = 3) -> list[dict]:
    if not bars:
        return []
    mr = median_bar_range(bars)
    if mr <= 0:
        return []

    radius = mr * 0.45
    min_half = mr * 0.12
    points: list[WeightedResidual] = []
    for idx, b in enumerate(bars):
        base = line_value(b.time, base_t1, base_p1, base_slope)
        body_low = min(b.open, b.close)
        body_high = max(b.open, b.close)
        points.extend([
            WeightedResidual(body_low - base, 1.50, idx, "BODY_LOW"),
            WeightedResidual(body_high - base, 1.50, idx, "BODY_HIGH"),
            WeightedResidual(b.low - base, 0.75, idx, "WICK_LOW"),
            WeightedResidual(b.high - base, 0.75, idx, "WICK_HIGH"),
        ])

    points.sort(key=lambda p: p.value)
    clusters: list[list[WeightedResidual]] = []
    current: list[WeightedResidual] = []
    center = None
    for p in points:
        if not current:
            current = [p]
            center = p.value
            continue
        assert center is not None
        if abs(p.value - center) <= radius:
            current.append(p)
            center = sum(x.value * x.weight for x in current) / sum(x.weight for x in current)
        else:
            clusters.append(current)
            current = [p]
            center = p.value
    if current:
        clusters.append(current)

    candidates = []
    n = max(1, len(bars))
    for pts in clusters:
        unique_bars = len({p.bar_index for p in pts})
        body_weight = sum(p.weight for p in pts if p.kind.startswith("BODY"))
        wick_weight = sum(p.weight for p in pts if p.kind.startswith("WICK"))
        if unique_bars < 4 or body_weight < 6.0:
            continue
        low = weighted_quantile(pts, 0.20)
        high = weighted_quantile(pts, 0.80)
        center = weighted_quantile(pts, 0.50)
        if high - low < min_half * 2:
            low = center - min_half
            high = center + min_half
        recent = max(p.bar_index for p in pts) / n
        score = unique_bars * 2.0 + body_weight + wick_weight * 0.5 + recent * 2.0
        candidates.append({
            "low_offset": low,
            "high_offset": high,
            "center_offset": center,
            "score": score,
            "unique_bars": unique_bars,
            "body_weight": body_weight,
            "wick_weight": wick_weight,
        })

    # Strongest non-overlapping bands survive. Any overlap suppresses the
    # weaker band; we never merge two bands into one opaque wide zone.
    selected: list[dict] = []
    min_center_gap = mr * 1.25
    for c in sorted(candidates, key=lambda x: (-x["score"], x["center_offset"])):
        overlap_or_too_close = False
        for existing in selected:
            overlaps = max(c["low_offset"], existing["low_offset"]) <= min(c["high_offset"], existing["high_offset"])
            too_close = abs(c["center_offset"] - existing["center_offset"]) < min_center_gap
            if overlaps or too_close:
                overlap_or_too_close = True
                break
        if overlap_or_too_close:
            continue
        selected.append(c)
        if len(selected) >= max_zones:
            break
    selected.sort(key=lambda x: x["center_offset"])
    for i, z in enumerate(selected, 1):
        z["zone_no"] = i
        z["reason_code"] = "PARALLEL_REACTION_ZONE_BODY_WICK_CLUSTER"
    return selected


def choose_updated_ch(pivots, *, base_t1, base_p1, base_t2, base_p2, base_ch_offset, tolerance) -> dict | None:
    slope = slope_per_second(base_t1, base_p1, base_t2, base_p2)
    highs = [p for p in pivots if p.kind == "HIGH" and p.time > base_t2]
    if not highs:
        return None
    candidates = []
    for h in highs:
        offset = h.price - line_value(h.time, base_t1, base_p1, slope)
        if offset <= float(base_ch_offset) + tolerance:
            continue
        candidates.append((h.time, offset, h))
    if not candidates:
        return None
    _, offset, h = max(candidates, key=lambda x: x[0])
    return {
        "high_time": h.time,
        "high_price": float(h.price),
        "confirmed_by_time": h.confirmed_by_time,
        "offset": float(offset),
        "reason_code": "UPDATED_CHANNEL_HIGH_CONFIRMED_38_PIVOT",
    }


def write_row(rows, *, object_id, symbol, timeframe, structure, role, t1, p1, t2, p2, status):
    rows.append([
        object_id, symbol, timeframe, structure, role,
        mt4_time(t1), f"{float(p1):.8f}", mt4_time(t2), f"{float(p2):.8f}",
        "EXPERIMENTAL", "1", status, "RAY_RIGHT",
    ])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--symbol", default="USDJPY#")
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    refdoc = json.loads(Path(args.reference).read_text(encoding="utf-8-sig"))
    rows = []
    audit = {
        "schema": "nvt9-structural-overlay-0919/0.1",
        "audit_id": "ID10IQ200",
        "research_only": True,
        "production_changed": False,
        "d1_continuation": {"status": "NOT_BUILT"},
        "h1_native_continuation": {"status": "NOT_BUILT"},
        "h1_reaction_zones": {"status": "NOT_BUILT"},
        "h1_updated_ch": {"status": "NOT_BUILT"},
    }

    # ---- D1 continuation support TL + Decision HL ----
    d1_path = input_dir / f"NVT_{safe_symbol_filename(args.symbol)}_D1.csv"
    if d1_path.exists():
        d1_all = load_ohlc_csv(d1_path)
        d1 = [b for b in d1_all if b.time < CUTOFF][-600:]
        piv = detect_turns(d1).pivots
        cand = build_d1_continuation(d1, piv)
        if cand is not None:
            end = d1[-1].time
            tl2 = line_value(end, cand.anchor1.time, cand.anchor1.price, cand.slope)
            ch1 = cand.anchor1.price + cand.ch_offset
            ch2 = tl2 + cand.ch_offset
            write_row(rows, object_id="X0919-D1-CONT-01-TL", symbol=args.symbol, timeframe="D1",
                      structure="CONTINUATION_SUPPORT", role="CONT_TL",
                      t1=cand.anchor1.time, p1=cand.anchor1.price, t2=end, p2=tl2, status=cand.status)
            write_row(rows, object_id="X0919-D1-CONT-01-CH", symbol=args.symbol, timeframe="D1",
                      structure="CONTINUATION_SUPPORT", role="CONT_CH",
                      t1=cand.anchor1.time, p1=ch1, t2=end, p2=ch2, status=cand.status)
            write_row(rows, object_id="X0919-D1-CONT-01-HL", symbol=args.symbol, timeframe="D1",
                      structure="CONTINUATION_SUPPORT", role="CONT_HL",
                      t1=cand.decision_hl.time, p1=cand.decision_hl.price, t2=end, p2=cand.decision_hl.price, status=cand.status)
            audit["d1_continuation"] = {
                "status": "BUILT",
                "object_family": "X0919-D1-CONT-01",
                "reason_code": "D1_CONTINUATION_SUPPORT_TIGHTEST_UNBROKEN_BROAD_PRE_BREAK" if cand.hl_break_time is None else "D1_CONTINUATION_SUPPORT_TIGHTEST_UNBROKEN_BROAD_ACTIVE",
                "anchor1": {"time": cand.anchor1.time.isoformat(), "price": float(cand.anchor1.price)},
                "anchor2": {"time": cand.anchor2.time.isoformat(), "price": float(cand.anchor2.price)},
                "decision_hl": {
                    "time": cand.decision_hl.time.isoformat(),
                    "price": float(cand.decision_hl.price),
                    "break_time": cand.hl_break_time.isoformat() if cand.hl_break_time else None,
                },
                "tl_contacts": cand.tl_contacts,
                "duration_days": cand.duration_days,
                "unbroken_close": cand.unbroken_close,
                "ch_anchor": {"time": cand.ch_anchor.time.isoformat(), "price": float(cand.ch_anchor.price)},
                "ch_offset": cand.ch_offset,
                "visibility_semantics": "REFERENCE_BEFORE_HL_BREAK; ACTIVE_AFTER_HL_BREAK",
                "new_direction_gate_bypassed": True,
                "bypass_reason": "Same-direction continuation support is visible as reference and does not claim a new-direction regime switch.",
                "selector_policy": "TIGHTEST_UNBROKEN_BROAD_SUPPORT",
                "selector_min_broad_days": 120.0,
                "rejected_policy": "LONGEST_DURATION_FIRST",
                "rejected_policy_reason": "Visual audit showed the duration-first selector can choose an obsolete shallow D1 line below the active support structure.",
            }

    # ---- H1 native TL/HL + parallel reaction zones + updated CH ----
    h1_path = input_dir / f"NVT_{safe_symbol_filename(args.symbol)}_H1.csv"
    if h1_path.exists():
        h1_all = load_ohlc_csv(h1_path)
        h1 = [b for b in h1_all if b.time < CUTOFF][-600:]
        h1_turns = detect_turns(h1)
        h1_cand = build_h1_native_continuation(h1, h1_turns.pivots)

        if h1_cand is not None:
            end = h1[-1].time
            tl_end = line_value(end, h1_cand.anchor1.time, h1_cand.anchor1.price, h1_cand.slope)
            ch_start = h1_cand.anchor1.price + h1_cand.ch_offset
            ch_end = tl_end + h1_cand.ch_offset

            write_row(rows, object_id="X0919-H1-CONT-01-TL", symbol=args.symbol, timeframe="H1",
                      structure="H1_NATIVE_CONTINUATION", role="CONT_TL",
                      t1=h1_cand.anchor1.time, p1=h1_cand.anchor1.price, t2=end, p2=tl_end, status=h1_cand.status)
            write_row(rows, object_id="X0919-H1-CONT-01-CH", symbol=args.symbol, timeframe="H1",
                      structure="H1_NATIVE_CONTINUATION", role="CONT_CH",
                      t1=h1_cand.anchor1.time, p1=ch_start, t2=end, p2=ch_end, status=h1_cand.status)
            write_row(rows, object_id="X0919-H1-CONT-01-HL", symbol=args.symbol, timeframe="H1",
                      structure="H1_NATIVE_CONTINUATION", role="CONT_HL",
                      t1=h1_cand.decision_hl.time, p1=h1_cand.decision_hl.price,
                      t2=end, p2=h1_cand.decision_hl.price, status=h1_cand.status)

            audit["h1_native_continuation"] = {
                "status": "BUILT",
                "object_family": "X0919-H1-CONT-01",
                "reason_code": "H1_NATIVE_RECENT_TIGHT_UNBROKEN_CONTINUATION",
                "anchor1": {"time": h1_cand.anchor1.time.isoformat(), "price": float(h1_cand.anchor1.price)},
                "anchor2": {"time": h1_cand.anchor2.time.isoformat(), "price": float(h1_cand.anchor2.price)},
                "decision_hl": {
                    "time": h1_cand.decision_hl.time.isoformat(),
                    "price": float(h1_cand.decision_hl.price),
                    "break_time": h1_cand.hl_break_time.isoformat() if h1_cand.hl_break_time else None,
                },
                "tl_contacts": h1_cand.tl_contacts,
                "duration_days": h1_cand.duration_days,
                "ch_anchor": {"time": h1_cand.ch_anchor.time.isoformat(), "price": float(h1_cand.ch_anchor.price)},
                "ch_offset": h1_cand.ch_offset,
                "source_timeframe": "H1",
                "mapped_lower_tf_used_as_base": False,
            }

            # Reaction zones are now based on the H1-native TL slope, not R0919-08/M15.
            start = h1_cand.anchor1.time
            zone_bars = [bar for bar in h1 if bar.time >= start]
            zones = cluster_reaction_zones(
                zone_bars,
                base_t1=h1_cand.anchor1.time,
                base_p1=h1_cand.anchor1.price,
                base_slope=h1_cand.slope,
                max_zones=3,
            )

            for z in zones:
                zid = f"X0919-H1-Z{z['zone_no']:02d}"
                low1 = line_value(start, h1_cand.anchor1.time, h1_cand.anchor1.price, h1_cand.slope, z["low_offset"])
                low2 = line_value(end, h1_cand.anchor1.time, h1_cand.anchor1.price, h1_cand.slope, z["low_offset"])
                high1 = line_value(start, h1_cand.anchor1.time, h1_cand.anchor1.price, h1_cand.slope, z["high_offset"])
                high2 = line_value(end, h1_cand.anchor1.time, h1_cand.anchor1.price, h1_cand.slope, z["high_offset"])
                write_row(rows, object_id=zid+"-LOW", symbol=args.symbol, timeframe="H1",
                          structure="PARALLEL_REACTION_ZONE", role="REACTION_ZONE_LOW",
                          t1=start, p1=low1, t2=end, p2=low2, status="ACTIVE")
                write_row(rows, object_id=zid+"-HIGH", symbol=args.symbol, timeframe="H1",
                          structure="PARALLEL_REACTION_ZONE", role="REACTION_ZONE_HIGH",
                          t1=start, p1=high1, t2=end, p2=high2, status="ACTIVE")

            audit["h1_reaction_zones"] = {
                "status": "BUILT" if zones else "NO_ZONE_PASSED",
                "base_reference_id": "X0919-H1-CONT-01",
                "reason_code": "H1_NATIVE_PARALLEL_REACTION_ZONE_BODY_WICK_CLUSTER",
                "slope_per_second": h1_cand.slope,
                "analysis_start": start.isoformat(),
                "analysis_end": end.isoformat(),
                "zone_count": len(zones),
                "non_overlap_policy": "WEAKER_OVERLAP_OR_TOO_CLOSE_ZONE_SUPPRESSED",
                "max_zones": 3,
                "minimum_center_gap_median_range_multiple": 1.25,
                "minimum_unique_bars": 4,
                "minimum_body_weight": 6.0,
                "body_weight": 1.5,
                "wick_weight": 0.75,
                "zones": zones,
            }

            tol = max(median_bar_range(h1) * 0.25, 1e-8)
            uch = choose_updated_ch(
                h1_turns.pivots,
                base_t1=h1_cand.anchor1.time,
                base_p1=h1_cand.anchor1.price,
                base_t2=h1_cand.anchor2.time,
                base_p2=h1_cand.anchor2.price,
                base_ch_offset=h1_cand.ch_offset,
                tolerance=tol,
            )
            if uch is not None:
                p1 = line_value(start, h1_cand.anchor1.time, h1_cand.anchor1.price, h1_cand.slope, uch["offset"])
                p2 = line_value(end, h1_cand.anchor1.time, h1_cand.anchor1.price, h1_cand.slope, uch["offset"])
                write_row(rows, object_id="X0919-H1-UCH-01", symbol=args.symbol, timeframe="H1",
                          structure="UPDATED_CHANNEL", role="UPDATED_CH",
                          t1=start, p1=p1, t2=end, p2=p2, status="ACTIVE")
                audit["h1_updated_ch"] = {
                    "status": "BUILT",
                    **{k:(v.isoformat() if isinstance(v, datetime) else v) for k,v in uch.items()},
                    "base_reference_id": "X0919-H1-CONT-01",
                    "old_ch_offset": h1_cand.ch_offset,
                    "new_ch_offset": uch["offset"],
                    "tolerance": tol,
                }
            else:
                audit["h1_updated_ch"] = {
                    "status": "NO_CONFIRMED_HIGH_OUTSIDE_EXISTING_CH",
                    "base_reference_id": "X0919-H1-CONT-01",
                    "old_ch_offset": h1_cand.ch_offset,
                    "tolerance": tol,
                }
        else:
            audit["h1_native_continuation"] = {
                "status": "NO_H1_NATIVE_CONTINUATION_PASSED",
                "reason_code": "DO_NOT_FALL_BACK_TO_MAPPED_M15_AS_H1_NATIVE",
            }
            audit["h1_reaction_zones"] = {
                "status": "NOT_BUILT_NO_H1_NATIVE_BASE",
            }
            audit["h1_updated_ch"] = {
                "status": "NOT_BUILT_NO_H1_NATIVE_BASE",
            }

    header = [
        "object_id","symbol","timeframe","structure_level","role",
        "t1","p1","t2","p2","generation_role","generation","status","extent",
    ]
    csv_path = outdir / "NVT9_0919_STRUCTURAL_OVERLAY.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    json_path = outdir / "NVT9_0919_STRUCTURAL_OVERLAY_AUDIT.json"
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    txt_path = outdir / "NVT9_0919_STRUCTURAL_OVERLAY_AUDIT.txt"
    txt = [
        "NVT9 09/19 STRUCTURAL OVERLAY AUDIT",
        "Audit ID: ID10IQ200",
        "",
        f"D1 continuation: {audit['d1_continuation'].get('status')} {audit['d1_continuation'].get('reason_code')}",
        f"H1 native TL/HL: {audit['h1_native_continuation'].get('status')} {audit['h1_native_continuation'].get('reason_code')}",
        f"H1 reaction zones: {audit['h1_reaction_zones'].get('status')} count={audit['h1_reaction_zones'].get('zone_count', 0)}",
        f"H1 updated CH: {audit['h1_updated_ch'].get('status')} {audit['h1_updated_ch'].get('reason_code')}",
        "",
        "Production is unchanged. These objects are research-only.",
    ]
    txt_path.write_text("\n".join(txt), encoding="utf-8")

    print(json.dumps({
        "status": "PASS_STRUCTURAL_OVERLAY_BUILD",
        "row_count": len(rows),
        "csv": str(csv_path),
        "audit_json": str(json_path),
        "audit_txt": str(txt_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
