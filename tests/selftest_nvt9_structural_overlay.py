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
    build_d1_retained_reference_0912,
    build_d1_major_channel,
    build_h1_native_continuation,
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

    # 09/12 retained D1 reference: reproduce the GT_0004/NVT5
    # evidence-window family rather than filtering it out for being old/far.
    rt0 = datetime(2025, 4, 1)
    retained_bars = []
    for i in range(540):
        t = rt0 + timedelta(days=i)
        # Keep closes safely above the intended retained support.
        close = 147.0 + i * 0.02
        retained_bars.append(Bar(t, close, close + 1.0, close - 0.8, close))
    retained = build_d1_retained_reference_0912(retained_bars, [
        Pivot("LOW", 3, datetime(2025, 4, 4), 144.544, 6, datetime(2025, 4, 7), 0.38),
        Pivot("HIGH", 80, datetime(2025, 6, 23), 148.0, 81, datetime(2025, 6, 24), 0.38),
        Pivot("LOW", 161, datetime(2025, 9, 9), 146.302, 164, datetime(2025, 9, 12), 0.38),
        Pivot("HIGH", 163, datetime(2025, 9, 11), 148.179, 166, datetime(2025, 9, 14), 0.38),
        Pivot("LOW", 169, datetime(2025, 9, 17), 145.476, 172, datetime(2025, 9, 20), 0.38),
    ])
    assert retained is not None
    assert retained.anchor1.time == datetime(2025, 4, 4)
    assert retained.anchor2.time == datetime(2025, 9, 9)
    assert retained.ch_anchor.time == datetime(2025, 9, 11)
    assert retained.unbroken_close is True

    # 09/12 D1 major channel: a multi-month rising support family must be
    # available separately from the tight continuation selector.
    major_bars = []
    mt0 = datetime(2025, 11, 1)
    for i in range(300):
        t = mt0 + timedelta(days=i)
        base = 120.0 + i * 0.004
        major_bars.append(Bar(t, base, base + 1.0, base - 1.0, base + 0.2))
    major_a1 = Pivot("LOW", 0, mt0, 100.0, 1, mt0 + timedelta(days=1), 0.38)
    major_h1 = Pivot("HIGH", 90, mt0 + timedelta(days=90), 118.0, 91, mt0 + timedelta(days=91), 0.38)
    major_a2 = Pivot("LOW", 180, mt0 + timedelta(days=180), 110.0, 181, mt0 + timedelta(days=181), 0.38)
    major_h2 = Pivot("HIGH", 250, mt0 + timedelta(days=250), 124.0, 251, mt0 + timedelta(days=251), 0.38)
    major = build_d1_major_channel(major_bars, [major_a1, major_h1, major_a2, major_h2])
    assert major is not None
    assert major.duration_days >= 120.0
    assert major.anchor1.time == major_a1.time
    assert major.anchor2.time == major_a2.time
    assert major.ch_offset > 0

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
    assert 1 <= len(zones) <= 3
    for i, a in enumerate(zones):
        for b in zones[i + 1:]:
            assert max(a["low_offset"], b["low_offset"]) > min(a["high_offset"], b["high_offset"])

    # H1-native continuation must be constructible independently from any M15 reference.
    # Use a >2-day structure, matching the intended Sep14 -> Sep17 class of H1 swing.
    h1_native_bars = []
    for i in range(96):
        t = start + timedelta(hours=i)
        base = 154.9 + i * 0.012
        h1_native_bars.append(Bar(t, base, base + 0.25, base - 0.15, base + 0.08))
    h1_native = build_h1_native_continuation(h1_native_bars, [
        Pivot("LOW", 0, start, 154.8, 1, start + timedelta(hours=1), 0.38),
        Pivot("HIGH", 36, start + timedelta(hours=36), 156.5, 37, start + timedelta(hours=37), 0.38),
        Pivot("LOW", 72, start + timedelta(hours=72), 155.7, 73, start + timedelta(hours=73), 0.38),
    ])
    assert h1_native is not None
    assert h1_native.anchor1.time == start
    assert h1_native.anchor2.time == start + timedelta(hours=72)
    assert h1_native.decision_hl.price == 156.5

    # H1 formation-valid fallback: a projected line may have been crossed
    # before anchor2 existed, but after anchor2 it must remain intact.  The
    # Decision HL must stay tied to this same native H1 family.
    fb_start = datetime(2026, 9, 8)
    fb_bars = []
    for i in range(84):
        t = fb_start + timedelta(hours=i)
        line = 100.0 + (4.0 / 48.0) * i
        close = line + 1.0
        if i == 24:
            close = line - 0.8
        if i > 48:
            close = line + 1.2
        fb_bars.append(Bar(t, close, close + 0.4, close - 0.4, close))
    fb = build_h1_native_continuation(fb_bars, [
        Pivot("LOW", 0, fb_start, 100.0, 1, fb_start + timedelta(hours=1), 0.38),
        Pivot("HIGH", 28, fb_start + timedelta(hours=28), 108.0, 29, fb_start + timedelta(hours=29), 0.38),
        Pivot("LOW", 48, fb_start + timedelta(hours=48), 104.0, 49, fb_start + timedelta(hours=49), 0.38),
    ])
    assert fb is not None
    assert fb.unbroken_close is False
    assert fb.decision_hl.price == 108.0
    assert fb.anchor2.time == fb_start + timedelta(hours=48)

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
