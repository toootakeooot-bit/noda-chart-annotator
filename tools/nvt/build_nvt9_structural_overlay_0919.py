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


def build_d1_visual_truth_0912(bars, pivots, visual_truth: dict) -> tuple[ContinuationCandidate, datetime | None, dict] | None:
    """Resolve the user-annotated 09/12 D1 outer support against confirmed pivots.

    The two yellow-circle areas are evidence windows, not independent "take
    the lowest pivot" instructions.  All LOW/LOW pairs inside the two windows
    are tested as one geometry.  The approved TL must sit under every D1 wick
    from anchor1 through anchor2; a line that cuts through even one formation
    wick is rejected.  Among valid envelope lines, prefer the pair with more
    wick contacts and the smallest mean wick gap (tightest outer support).
    A later post-anchor2 break is lifecycle evidence and does not delete the
    historical reference.
    """
    approved = [
        row for row in (visual_truth.get("approved_families") or [])
        if row.get("truth_id") == "VT0912-D1-001"
    ]
    if not approved:
        return None
    spec = approved[0]

    lows = [p for p in pivots if p.kind == "LOW"]
    highs = [p for p in pivots if p.kind == "HIGH"]
    if len(lows) < 2 or not highs or not bars:
        return None

    a1_lo = datetime.fromisoformat(spec["anchor1"]["window_start"])
    a1_hi = datetime.fromisoformat(spec["anchor1"]["window_end"])
    a2_lo = datetime.fromisoformat(spec["anchor2"]["window_start"])
    a2_hi = datetime.fromisoformat(spec["anchor2"]["window_end"])
    anchor1_pool = [p for p in lows if a1_lo <= p.time <= a1_hi]
    anchor2_pool = [p for p in lows if a2_lo <= p.time <= a2_hi]
    if not anchor1_pool or not anchor2_pool:
        return None

    mr = max(median_bar_range(bars), 1e-8)
    wick_tol = max(mr * 0.03, 1e-8)
    contact_tol = max(mr * 0.12, wick_tol)
    pair_candidates: list[tuple[object, object, float, int, float, float]] = []

    for a in anchor1_pool:
        for b in anchor2_pool:
            if b.time <= a.time or b.price <= a.price:
                continue
            slope = slope_per_second(a.time, a.price, b.time, b.price)
            if slope <= 0:
                continue

            formation_bars = [bar for bar in bars if a.time <= bar.time <= b.time]
            if not formation_bars:
                continue

            gaps = [
                float(bar.low) - line_value(bar.time, a.time, a.price, slope)
                for bar in formation_bars
            ]
            breach_count = sum(1 for gap in gaps if gap < -wick_tol)
            if breach_count:
                continue

            contact_count = sum(1 for gap in gaps if abs(gap) <= contact_tol)
            mean_gap = sum(max(0.0, gap) for gap in gaps) / len(gaps)
            min_gap = min(gaps)
            pair_candidates.append((a, b, slope, contact_count, mean_gap, min_gap))

    if not pair_candidates:
        return None

    # Supporting-envelope semantics: contact evidence first, then the line
    # that runs closest under the intervening wick lows.  This rejects an
    # inner line when a wick is outside it and avoids selecting a needlessly
    # low line merely because it is older.
    a, b, slope, formation_contacts, formation_mean_gap, formation_min_gap = max(
        pair_candidates,
        key=lambda item: (
            item[3],
            -item[4],
            -item[1].time.timestamp(),
            -abs(item[2]),
        ),
    )

    between = [h for h in highs if a.time < h.time < b.time]
    if not between:
        return None
    decision_hl = max(between, key=lambda p: (p.price, p.time))
    break_tol = max(mr * 0.28, 1e-8)

    break_time = None
    for bar in bars:
        if bar.time <= b.time:
            continue
        if bar.close < line_value(bar.time, a.time, a.price, slope) - break_tol:
            break_time = bar.time
            break

    contacts = sum(
        1
        for p in lows
        if p.time >= a.time
        and abs(p.price - line_value(p.time, a.time, a.price, slope)) <= contact_tol
    )

    # Updated channel may use a later confirmed high, but the TL anchors stay
    # fixed to the user-approved outer support geometry.
    high_pool = [h for h in highs if h.time > a.time]
    residuals = [
        (h.price - line_value(h.time, a.time, a.price, slope), h)
        for h in high_pool
    ]
    residuals = [(off, h) for off, h in residuals if off > 0]
    if not residuals:
        return None
    ch_offset, ch_anchor = max(residuals, key=lambda x: (x[0], x[1].time))

    hl_break_time = None
    for bar in bars:
        if bar.time <= b.time:
            continue
        if bar.close > decision_hl.price:
            hl_break_time = bar.time
            break

    cand = ContinuationCandidate(
        anchor1=a,
        anchor2=b,
        decision_hl=decision_hl,
        slope=slope,
        tl_contacts=contacts,
        duration_days=(b.time - a.time).total_seconds() / 86400.0,
        unbroken_close=(break_time is None),
        hl_break_time=hl_break_time,
        ch_anchor=ch_anchor,
        ch_offset=ch_offset,
        tolerance=break_tol,
    )
    resolved = {
        "truth_id": spec["truth_id"],
        "anchor1_window": [spec["anchor1"]["window_start"], spec["anchor1"]["window_end"]],
        "anchor2_window": [spec["anchor2"]["window_start"], spec["anchor2"]["window_end"]],
        "anchor_selection": "PAIRWISE_OUTERMOST_WICK_ENVELOPE",
        "formation_wick_breach_count": 0,
        "formation_wick_contact_count": formation_contacts,
        "formation_mean_wick_gap": formation_mean_gap,
        "formation_min_wick_gap": formation_min_gap,
        "formation_wick_tolerance": wick_tol,
        "contact_tolerance": contact_tol,
        "retain_after_break": bool((spec.get("lifecycle") or {}).get("retain_after_closed_bar_break")),
    }
    return cand, break_time, resolved


def build_d1_retained_reference_0912(bars, pivots) -> ContinuationCandidate | None:
    """Rebuild the retained D1 rising reference for the 09/12 historical audit.

    Evidence basis is the frozen NVT5/GT_0004 visual probe:
      - rising MAJOR monitoring reference
      - anchor1 in the early-April-2025 window
      - anchor2 in the late-August/September-2025 low cluster
      - original geometry retained instead of newest re-anchoring

    This is historical audit reconstruction only, not a production selector.
    """
    lows = [p for p in pivots if p.kind == "LOW"]
    highs = [p for p in pivots if p.kind == "HIGH"]
    if len(lows) < 2 or not highs or not bars:
        return None

    a1_lo = datetime.fromisoformat("2025-04-01T00:00:00")
    a1_hi = datetime.fromisoformat("2025-04-20T23:59:59")
    a2_lo = datetime.fromisoformat("2025-08-20T00:00:00")
    a2_hi = datetime.fromisoformat("2025-09-25T23:59:59")
    tol = max(median_bar_range(bars) * 0.28, 1e-8)
    candidates: list[ContinuationCandidate] = []

    anchor1s = [p for p in lows if a1_lo <= p.time <= a1_hi]
    anchor2s = [p for p in lows if a2_lo <= p.time <= a2_hi]

    for a in anchor1s:
        for b in anchor2s:
            if b.time <= a.time or b.price <= a.price:
                continue

            slope = slope_per_second(a.time, a.price, b.time, b.price)
            if slope <= 0:
                continue

            # The retained reference must be a genuine confirmed-pivot
            # structure and must remain a valid support by closed bars.
            broken = any(
                bar.time >= a.time
                and bar.close < line_value(bar.time, a.time, a.price, slope) - tol
                for bar in bars
            )
            if broken:
                continue

            between = [h for h in highs if a.time < h.time < b.time]
            if not between:
                continue
            decision_hl = max(between, key=lambda p: (p.price, p.time))

            contacts = sum(
                1
                for p in lows
                if p.time >= a.time
                and abs(p.price - line_value(p.time, a.time, a.price, slope)) <= tol
            )

            hl_break_time = None
            for bar in bars:
                if bar.time <= b.time:
                    continue
                if bar.close > decision_hl.price:
                    hl_break_time = bar.time
                    break

            # Freeze the ORIGINAL channel geometry near formation.  Do not let
            # a 2026 high silently re-anchor/expand the retained 2025 channel.
            ch_window_end = b.time + timedelta(days=30)
            high_pool = [
                h for h in highs
                if a.time < h.time <= ch_window_end
            ]
            residuals = [
                (h.price - line_value(h.time, a.time, a.price, slope), h)
                for h in high_pool
            ]
            residuals = [(off, h) for off, h in residuals if off > 0]
            if not residuals:
                continue

            # Prefer a channel contact at/after anchor2 when available, matching
            # the original formed channel rather than a pre-anchor2 extreme.
            post_a2 = [(off, h) for off, h in residuals if h.time >= b.time]
            pool = post_a2 if post_a2 else residuals
            ch_offset, ch_anchor = max(pool, key=lambda x: (x[0], -abs((x[1].time - b.time).total_seconds())))

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

    # Within the NVT5 evidence windows, preserve the earliest established
    # retained geometry when contact evidence is comparable.  Do not let a
    # later/gentler re-anchor silently replace the original monitoring line.
    return max(
        candidates,
        key=lambda c: (
            c.tl_contacts,
            -c.anchor2.time.timestamp(),
            -abs(c.slope),
        ),
    )


def build_d1_major_channel(bars, pivots) -> ContinuationCandidate | None:
    """Build the broad rising D1 support/channel family used for 09/12 audit.

    This is deliberately distinct from the tight continuation family.  It
    favors a multi-month structure with repeated support contact, rejects
    lines that are too far below the current market, and requires the line to
    remain valid after anchor2 is formed.
    """
    lows = [p for p in pivots if p.kind == "LOW"]
    highs = [p for p in pivots if p.kind == "HIGH"]
    if len(lows) < 2 or not highs or not bars:
        return None

    mr = max(median_bar_range(bars), 1e-8)
    tol = max(mr * 0.30, 1e-8)
    cutoff_time = bars[-1].time
    cutoff_close = float(bars[-1].close)
    candidates: list[tuple[ContinuationCandidate, float]] = []

    for i, a in enumerate(lows[:-1]):
        anchor_age_days = (cutoff_time - a.time).total_seconds() / 86400.0
        if anchor_age_days > 480.0:
            continue
        for b in lows[i + 1:]:
            duration_days = (b.time - a.time).total_seconds() / 86400.0
            if duration_days < 120.0:
                continue
            if b.price <= a.price:
                continue

            between = [h for h in highs if a.time < h.time < b.time]
            if not between:
                continue
            slope = slope_per_second(a.time, a.price, b.time, b.price)
            if slope <= 0:
                continue

            # The line becomes actionable only after anchor2 exists.  From that
            # point forward, a meaningful D1 support must not be closed through.
            if any(
                bar.time > b.time
                and bar.close < line_value(bar.time, a.time, a.price, slope) - tol
                for bar in bars
            ):
                continue

            projected = line_value(cutoff_time, a.time, a.price, slope)
            gap = cutoff_close - projected
            if gap < -tol:
                continue
            if gap > max(mr * 5.0, 6.0):
                continue

            contacts = sum(
                1
                for p in lows
                if p.time >= a.time
                and abs(p.price - line_value(p.time, a.time, a.price, slope)) <= tol
            )
            decision_hl = max(between, key=lambda p: (p.price, p.time))

            hl_break_time = None
            for bar in bars:
                if bar.time <= b.time:
                    continue
                if bar.close > decision_hl.price:
                    hl_break_time = bar.time
                    break

            high_pool = [h for h in highs if h.time >= a.time]
            residuals = [
                (h.price - line_value(h.time, a.time, a.price, slope), h)
                for h in high_pool
            ]
            residuals = [(off, h) for off, h in residuals if off > tol]
            if not residuals:
                continue
            ch_offset, ch_anchor = max(residuals, key=lambda x: (x[0], x[1].time))

            cand = ContinuationCandidate(
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
            candidates.append((cand, gap))

    if not candidates:
        return None

    # Major structure: repeated support evidence first, then broader span,
    # while preferring the line that still sits reasonably close to price.
    return max(
        candidates,
        key=lambda item: (
            item[0].tl_contacts,
            item[0].duration_days,
            -item[1],
            item[0].anchor2.time,
        ),
    )[0]


def build_h1_native_continuation(bars, pivots) -> ContinuationCandidate | None:
    """Build a native H1 rising TL/CH/Decision-HL family.

    Strict candidates are preferred.  If none survive, a formation-valid H1
    N-structure may be used when the line remains unbroken after anchor2.
    This keeps H1 ownership native and avoids falling back to mapped M15.
    """
    lows = [p for p in pivots if p.kind == "LOW"]
    highs = [p for p in pivots if p.kind == "HIGH"]
    if len(lows) < 2 or not highs:
        return None

    tol = max(median_bar_range(bars) * 0.28, 1e-8)
    recent_anchor2_times = {p.time for p in lows[-10:]}
    candidates: list[ContinuationCandidate] = []

    for i, a in enumerate(lows[:-1]):
        for b in lows[i + 1:]:
            if b.time not in recent_anchor2_times:
                continue
            duration_days = (b.time - a.time).total_seconds() / 86400.0
            if duration_days < 1.0:
                continue
            if b.price <= a.price:
                continue

            between = [h for h in highs if a.time < h.time < b.time]
            if not between:
                continue
            decision_hl = max(between, key=lambda p: (p.price, p.time))
            slope = slope_per_second(a.time, a.price, b.time, b.price)

            broken_full_life = any(
                bar.time >= a.time
                and bar.close < line_value(bar.time, a.time, a.price, slope) - tol
                for bar in bars
            )
            broken_after_anchor2 = any(
                bar.time > b.time
                and bar.close < line_value(bar.time, a.time, a.price, slope) - tol
                for bar in bars
            )
            if broken_after_anchor2:
                continue

            contacts = sum(
                1
                for p in lows
                if p.time >= a.time
                and abs(p.price - line_value(p.time, a.time, a.price, slope)) <= tol
            )

            hl_break_time = None
            for bar in bars:
                if bar.time <= b.time:
                    continue
                if bar.close > decision_hl.price:
                    hl_break_time = bar.time
                    break

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
                    unbroken_close=not broken_full_life,
                    hl_break_time=hl_break_time,
                    ch_anchor=ch_anchor,
                    ch_offset=ch_offset,
                    tolerance=tol,
                )
            )

    if not candidates:
        return None

    strict = [c for c in candidates if c.unbroken_close]
    pool = strict if strict else candidates

    cutoff_time = bars[-1].time
    cutoff_close = float(bars[-1].close)

    def rank(c: ContinuationCandidate):
        projected = line_value(cutoff_time, c.anchor1.time, c.anchor1.price, c.slope)
        gap = max(0.0, cutoff_close - projected)
        return (
            c.anchor2.time,
            -gap,
            c.tl_contacts,
            c.duration_days,
        )

    return max(pool, key=rank)


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
    ap.add_argument("--cutoff", default="2026-09-19T00:00:00")
    ap.add_argument("--case-tag", default="0919")
    ap.add_argument("--visual-truth")
    args = ap.parse_args()

    cutoff = datetime.fromisoformat(args.cutoff)
    case_tag = args.case_tag
    input_dir = Path(args.input_dir)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    refdoc = json.loads(Path(args.reference).read_text(encoding="utf-8-sig"))
    visual_truth = (
        json.loads(Path(args.visual_truth).read_text(encoding="utf-8-sig"))
        if args.visual_truth else {}
    )
    rows = []
    audit = {
        "schema": "nvt9-structural-overlay/0.2",
        "audit_id": "ID10IQ200",
        "case_tag": case_tag,
        "cutoff_exclusive": cutoff.isoformat(),
        "research_only": True,
        "production_changed": False,
        "d1_continuation": {"status": "NOT_BUILT"},
        "d1_major_channel": {"status": "NOT_BUILT"},
        "d1_visual_truth": {"status": "NOT_BUILT"},
        "h1_native_continuation": {"status": "NOT_BUILT"},
        "h1_reaction_zones": {"status": "NOT_BUILT"},
        "h1_updated_ch": {"status": "NOT_BUILT"},
    }

    # ---- D1 structure ----
    d1_path = input_dir / f"NVT_{safe_symbol_filename(args.symbol)}_D1.csv"
    if d1_path.exists():
        d1_all = load_ohlc_csv(d1_path)
        d1 = [bar for bar in d1_all if bar.time < cutoff][-600:]
        piv = detect_turns(d1).pivots
        cand = build_d1_continuation(d1, piv)
        truth_result = (
            build_d1_visual_truth_0912(d1, piv, visual_truth)
            if case_tag == "0912" and visual_truth else None
        )
        retained = None
        major = None
        if truth_result is None:
            retained = build_d1_retained_reference_0912(d1, piv) if case_tag == "0912" else None
            major = retained if retained is not None else (build_d1_major_channel(d1, piv) if case_tag == "0912" else None)
        end = d1[-1].time if d1 else None

        if truth_result is not None and end is not None:
            approved, tl_break_time, resolved_truth = truth_result
            tl2 = line_value(end, approved.anchor1.time, approved.anchor1.price, approved.slope)
            ch1 = approved.anchor1.price + approved.ch_offset
            ch2 = tl2 + approved.ch_offset
            lifecycle_status = "REFERENCE_RETAINED_BROKEN" if tl_break_time is not None else "ACTIVE_REFERENCE"
            write_row(rows, object_id=f"X{case_tag}-D1-APPROVED-01-TL", symbol=args.symbol, timeframe="D1",
                      structure="D1_USER_APPROVED_REFERENCE", role="APPROVED_TL",
                      t1=approved.anchor1.time, p1=approved.anchor1.price, t2=end, p2=tl2, status=lifecycle_status)
            write_row(rows, object_id=f"X{case_tag}-D1-APPROVED-01-CH", symbol=args.symbol, timeframe="D1",
                      structure="D1_USER_APPROVED_REFERENCE", role="APPROVED_CH",
                      t1=approved.anchor1.time, p1=ch1, t2=end, p2=ch2, status=lifecycle_status)
            write_row(rows, object_id=f"X{case_tag}-D1-APPROVED-01-HL", symbol=args.symbol, timeframe="D1",
                      structure="D1_USER_APPROVED_REFERENCE", role="APPROVED_HL",
                      t1=approved.decision_hl.time, p1=approved.decision_hl.price,
                      t2=end, p2=approved.decision_hl.price, status=lifecycle_status)

            audit["d1_visual_truth"] = {
                "status": "BUILT",
                "object_family": f"X{case_tag}-D1-APPROVED-01",
                "reason_code": "D1_USER_APPROVED_YELLOW_CIRCLE_LOW_PAIR",
                "anchor1": {
                    "kind": "LOW",
                    "time": approved.anchor1.time.isoformat(),
                    "price": float(approved.anchor1.price),
                    "confirmed_by_time": approved.anchor1.confirmed_by_time.isoformat(),
                },
                "anchor2": {
                    "kind": "LOW",
                    "time": approved.anchor2.time.isoformat(),
                    "price": float(approved.anchor2.price),
                    "confirmed_by_time": approved.anchor2.confirmed_by_time.isoformat(),
                },
                "decision_hl": {
                    "time": approved.decision_hl.time.isoformat(),
                    "price": float(approved.decision_hl.price),
                    "break_time": approved.hl_break_time.isoformat() if approved.hl_break_time else None,
                },
                "tl_break_time": tl_break_time.isoformat() if tl_break_time else None,
                "lifecycle_status": lifecycle_status,
                "ch_anchor": {
                    "time": approved.ch_anchor.time.isoformat(),
                    "price": float(approved.ch_anchor.price),
                    "confirmed_by_time": approved.ch_anchor.confirmed_by_time.isoformat(),
                },
                "ch_offset": approved.ch_offset,
                "resolved_truth": resolved_truth,
            }
            audit["d1_major_channel"] = {
                "status": "SUPERSEDED_BY_USER_APPROVED_D1_TRUTH",
                "reason_code": "DO_NOT_REPLACE_USER_APPROVED_ANCHOR_PAIR",
            }
            audit["d1_continuation"] = {
                "status": "SUPPRESSED_BY_USER_APPROVED_D1_TRUTH",
                "reason_code": "DO_NOT_REPLACE_USER_APPROVED_ANCHOR_PAIR",
            }

        # 09/12 visual audit prefers a user-approved pair first; broad major
        # channel is fallback only when no explicit visual truth is supplied.
        elif major is not None and end is not None:
            tl2 = line_value(end, major.anchor1.time, major.anchor1.price, major.slope)
            ch1 = major.anchor1.price + major.ch_offset
            ch2 = tl2 + major.ch_offset
            write_row(rows, object_id=f"X{case_tag}-D1-MAJOR-01-TL", symbol=args.symbol, timeframe="D1",
                      structure="D1_MAJOR_CHANNEL", role="MAJOR_TL",
                      t1=major.anchor1.time, p1=major.anchor1.price, t2=end, p2=tl2, status=major.status)
            write_row(rows, object_id=f"X{case_tag}-D1-MAJOR-01-CH", symbol=args.symbol, timeframe="D1",
                      structure="D1_MAJOR_CHANNEL", role="MAJOR_CH",
                      t1=major.anchor1.time, p1=ch1, t2=end, p2=ch2, status=major.status)
            write_row(rows, object_id=f"X{case_tag}-D1-MAJOR-01-HL", symbol=args.symbol, timeframe="D1",
                      structure="D1_MAJOR_CHANNEL", role="MAJOR_HL",
                      t1=major.decision_hl.time, p1=major.decision_hl.price,
                      t2=end, p2=major.decision_hl.price, status=major.status)
            audit["d1_major_channel"] = {
                "status": "BUILT",
                "object_family": f"X{case_tag}-D1-MAJOR-01",
                "reason_code": (
                    "D1_RETAINED_REFERENCE_GT0004_NVT5_WINDOW"
                    if retained is not None
                    else "D1_MAJOR_RISING_MULTI_MONTH_SUPPORT_CHANNEL"
                ),
                "anchor1": {"time": major.anchor1.time.isoformat(), "price": float(major.anchor1.price)},
                "anchor2": {"time": major.anchor2.time.isoformat(), "price": float(major.anchor2.price)},
                "decision_hl": {
                    "time": major.decision_hl.time.isoformat(),
                    "price": float(major.decision_hl.price),
                    "break_time": major.hl_break_time.isoformat() if major.hl_break_time else None,
                },
                "tl_contacts": major.tl_contacts,
                "duration_days": major.duration_days,
                "ch_anchor": {"time": major.ch_anchor.time.isoformat(), "price": float(major.ch_anchor.price)},
                "ch_offset": major.ch_offset,
                "selector_policy": (
                    "GT0004_RETAINED_REFERENCE_WINDOW_CONTACTS_GENTLER_SLOPE"
                    if retained is not None
                    else "MULTI_MONTH_RISING_SUPPORT_REPEATED_CONTACTS_THEN_SPAN"
                ),
                "historical_evidence_windows": (
                    {
                        "anchor1": ["2025-04-01T00:00:00", "2025-04-20T23:59:59"],
                        "anchor2": ["2025-08-20T00:00:00", "2025-09-25T23:59:59"],
                        "source": "NVT5_GT_0004_VISUAL_PROBE",
                        "production_generalization": False,
                    }
                    if retained is not None else None
                ),
            }
            audit["d1_continuation"] = {
                "status": "SUPPRESSED_BY_0912_MAJOR_CHANNEL",
                "reason_code": "REJECT_SHALLOW_DUPLICATE_WHEN_MAJOR_CHANNEL_AVAILABLE",
            }

        elif cand is not None and end is not None:
            tl2 = line_value(end, cand.anchor1.time, cand.anchor1.price, cand.slope)
            ch1 = cand.anchor1.price + cand.ch_offset
            ch2 = tl2 + cand.ch_offset
            write_row(rows, object_id=f"X{case_tag}-D1-CONT-01-TL", symbol=args.symbol, timeframe="D1",
                      structure="CONTINUATION_SUPPORT", role="CONT_TL",
                      t1=cand.anchor1.time, p1=cand.anchor1.price, t2=end, p2=tl2, status=cand.status)
            write_row(rows, object_id=f"X{case_tag}-D1-CONT-01-CH", symbol=args.symbol, timeframe="D1",
                      structure="CONTINUATION_SUPPORT", role="CONT_CH",
                      t1=cand.anchor1.time, p1=ch1, t2=end, p2=ch2, status=cand.status)
            write_row(rows, object_id=f"X{case_tag}-D1-CONT-01-HL", symbol=args.symbol, timeframe="D1",
                      structure="CONTINUATION_SUPPORT", role="CONT_HL",
                      t1=cand.decision_hl.time, p1=cand.decision_hl.price, t2=end, p2=cand.decision_hl.price, status=cand.status)
            audit["d1_continuation"] = {
                "status": "BUILT",
                "object_family": f"X{case_tag}-D1-CONT-01",
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
            }

    # ---- H1 native TL/HL + parallel reaction zones + updated CH ----
    h1_path = input_dir / f"NVT_{safe_symbol_filename(args.symbol)}_H1.csv"
    if h1_path.exists():
        h1_all = load_ohlc_csv(h1_path)
        h1 = [b for b in h1_all if b.time < cutoff][-600:]
        h1_turns = detect_turns(h1)
        h1_cand = build_h1_native_continuation(h1, h1_turns.pivots)

        if h1_cand is not None:
            end = h1[-1].time
            tl_end = line_value(end, h1_cand.anchor1.time, h1_cand.anchor1.price, h1_cand.slope)
            ch_start = h1_cand.anchor1.price + h1_cand.ch_offset
            ch_end = tl_end + h1_cand.ch_offset

            write_row(rows, object_id=f"X{case_tag}-H1-CONT-01-TL", symbol=args.symbol, timeframe="H1",
                      structure="H1_NATIVE_CONTINUATION", role="CONT_TL",
                      t1=h1_cand.anchor1.time, p1=h1_cand.anchor1.price, t2=end, p2=tl_end, status=h1_cand.status)
            write_row(rows, object_id=f"X{case_tag}-H1-CONT-01-CH", symbol=args.symbol, timeframe="H1",
                      structure="H1_NATIVE_CONTINUATION", role="CONT_CH",
                      t1=h1_cand.anchor1.time, p1=ch_start, t2=end, p2=ch_end, status=h1_cand.status)
            write_row(rows, object_id=f"X{case_tag}-H1-CONT-01-HL", symbol=args.symbol, timeframe="H1",
                      structure="H1_NATIVE_CONTINUATION", role="CONT_HL",
                      t1=h1_cand.decision_hl.time, p1=h1_cand.decision_hl.price,
                      t2=end, p2=h1_cand.decision_hl.price, status=h1_cand.status)

            audit["h1_native_continuation"] = {
                "status": "BUILT",
                "object_family": f"X{case_tag}-H1-CONT-01",
                "reason_code": (
                    "H1_NATIVE_RECENT_TIGHT_UNBROKEN_CONTINUATION"
                    if h1_cand.unbroken_close
                    else "H1_NATIVE_FORMATION_VALID_AFTER_ANCHOR2"
                ),
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
                "full_life_unbroken": h1_cand.unbroken_close,
                "post_anchor2_unbroken_required": True,
            }

            # Reaction zones are now based on the H1-native TL slope, not R0919-08/M15.
            start = h1_cand.anchor1.time
            zone_bars = [bar for bar in h1 if bar.time >= start]
            zones = cluster_reaction_zones(
                zone_bars,
                base_t1=h1_cand.anchor1.time,
                base_p1=h1_cand.anchor1.price,
                base_slope=h1_cand.slope,
                max_zones=(2 if case_tag == "0912" else 3),
            )

            for z in zones:
                zid = f"X{case_tag}-H1-Z{z['zone_no']:02d}"
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
                "base_reference_id": f"X{case_tag}-H1-CONT-01",
                "reason_code": "H1_NATIVE_PARALLEL_REACTION_ZONE_BODY_WICK_CLUSTER",
                "slope_per_second": h1_cand.slope,
                "analysis_start": start.isoformat(),
                "analysis_end": end.isoformat(),
                "zone_count": len(zones),
                "non_overlap_policy": "WEAKER_OVERLAP_OR_TOO_CLOSE_ZONE_SUPPRESSED",
                "max_zones": (2 if case_tag == "0912" else 3),
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
                write_row(rows, object_id=f"X{case_tag}-H1-UCH-01", symbol=args.symbol, timeframe="H1",
                          structure="UPDATED_CHANNEL", role="UPDATED_CH",
                          t1=start, p1=p1, t2=end, p2=p2, status="ACTIVE")
                audit["h1_updated_ch"] = {
                    "status": "BUILT",
                    **{k:(v.isoformat() if isinstance(v, datetime) else v) for k,v in uch.items()},
                    "base_reference_id": f"X{case_tag}-H1-CONT-01",
                    "old_ch_offset": h1_cand.ch_offset,
                    "new_ch_offset": uch["offset"],
                    "tolerance": tol,
                }
            else:
                audit["h1_updated_ch"] = {
                    "status": "NO_CONFIRMED_HIGH_OUTSIDE_EXISTING_CH",
                    "base_reference_id": f"X{case_tag}-H1-CONT-01",
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
        f"NVT9 {case_tag} STRUCTURAL OVERLAY AUDIT",
        "Audit ID: ID10IQ200",
        "",
        f"D1 continuation: {audit['d1_continuation'].get('status')} {audit['d1_continuation'].get('reason_code')}",
        f"D1 visual truth: {audit['d1_visual_truth'].get('status')} {audit['d1_visual_truth'].get('reason_code')}",
        f"D1 major channel: {audit['d1_major_channel'].get('status')} {audit['d1_major_channel'].get('reason_code')}",
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
