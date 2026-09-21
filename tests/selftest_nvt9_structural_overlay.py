from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from live_draw.model import Bar, Pivot
from tools.nvt.build_nvt9_structural_overlay_0919 import (
    build_d1_continuation,
    choose_updated_ch,
    cluster_reaction_zones,
)


def bars_for_continuation():
    t0 = datetime(2026, 1, 1)
    bars = []
    for i in range(16):
        t = t0 + timedelta(days=i)
        base = 100.0 + i * 0.5
        bars.append(Bar(t, base, base + 2.0, base - 1.0, base + 0.5))
    return bars


def main() -> None:
    # D1 continuation: LOW1 -> HIGH(HL) -> higher LOW2, but HL is NOT broken
    # after LOW2. The reference TL must still be buildable as PENDING.
    bars = bars_for_continuation()
    t0 = bars[0].time
    lows = [
        Pivot("LOW", 0, t0, 99.0, 1, t0 + timedelta(days=1), 0.38),
        Pivot("LOW", 10, t0 + timedelta(days=10), 104.0, 11, t0 + timedelta(days=11), 0.38),
    ]
    high = Pivot("HIGH", 5, t0 + timedelta(days=5), 112.0, 6, t0 + timedelta(days=6), 0.38)
    c = build_d1_continuation(bars, [lows[0], high, lows[1]])
    assert c is not None
    assert c.status == "REFERENCE_PENDING_HL_BREAK"
    assert c.decision_hl.price == 112.0
    assert c.anchor1.time == lows[0].time
    assert c.anchor2.time == lows[1].time

    # D1 selector regression: duration-first would choose the older/shallow A1.
    # The audited rule must choose the tighter still-unbroken broad support B1.
    t1 = datetime(2025, 1, 1)
    broad_bars = []
    for i in range(240):
        t = t1 + timedelta(days=i)
        base = 113.0 if i >= 200 else 120.0
        broad_bars.append(Bar(t, base, base + 1.0, base - 1.0, base))
    a1 = Pivot("LOW", 0, t1, 100.0, 1, t1 + timedelta(days=1), 0.38)
    b1 = Pivot("LOW", 40, t1 + timedelta(days=40), 101.0, 41, t1 + timedelta(days=41), 0.38)
    mid_high = Pivot("HIGH", 100, t1 + timedelta(days=100), 118.0, 101, t1 + timedelta(days=101), 0.38)
    a2 = Pivot("LOW", 200, t1 + timedelta(days=200), 110.0, 201, t1 + timedelta(days=201), 0.38)
    tight = build_d1_continuation(broad_bars, [a1, b1, mid_high, a2])
    assert tight is not None
    assert tight.duration_days >= 120.0
    assert tight.anchor1.time == b1.time
    assert tight.anchor2.time == a2.time
    assert tight.status == "REFERENCE_PENDING_HL_BREAK"

    # Reaction-zone clustering: construct repeated body/wick reactions around
    # separated residual bands; selected zones must never overlap.
    h1 = []
    start = datetime(2026, 9, 14)
    for i in range(24):
        t = start + timedelta(hours=i)
        center = 155.0 + i * 0.02
        band = 0.0 if i % 2 == 0 else 1.2
        o = center + band - 0.05
        close = center + band + 0.05
        h1.append(Bar(t, o, close + 0.12, o - 0.12, close))
    zones = cluster_reaction_zones(
        h1,
        base_t1=start,
        base_p1=155.0,
        base_slope=0.02 / 3600.0,
        max_zones=4,
    )
    assert 1 <= len(zones) <= 4
    for i, a in enumerate(zones):
        for b in zones[i + 1:]:
            assert max(a["low_offset"], b["low_offset"]) > min(a["high_offset"], b["high_offset"])

    # Updated CH requires a confirmed HIGH outside the existing CH by tolerance.
    base_t1 = start
    base_t2 = start + timedelta(hours=10)
    p1, p2 = 155.0, 156.0
    highs = [
        Pivot("HIGH", 12, start + timedelta(hours=12), 157.4, 13, start + timedelta(hours=13), 0.38),
        Pivot("HIGH", 18, start + timedelta(hours=18), 159.0, 19, start + timedelta(hours=19), 0.38),
    ]
    uch = choose_updated_ch(
        highs,
        base_t1=base_t1,
        base_p1=p1,
        base_t2=base_t2,
        base_p2=p2,
        base_ch_offset=1.0,
        tolerance=0.05,
    )
    assert uch is not None
    assert uch["high_time"] == highs[-1].time
    assert uch["reason_code"] == "UPDATED_CHANNEL_HIGH_CONFIRMED_38_PIVOT"

    print("NVT9_STRUCTURAL_OVERLAY_SELFTEST_PASS")


if __name__ == "__main__":
    main()
