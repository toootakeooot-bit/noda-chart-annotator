from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from live_draw.geometry import build_channel_candidates
from live_draw.model import Bar, Pivot
from live_draw.normal_run import hl_activation_event_end_indices_from_pivots


def main() -> int:
    t0 = datetime(2026, 7, 1, 0, 0)
    bars = []
    vals = [
        (100, 104, 99, 103),
        (103, 110, 102, 109),   # HIGH1
        (109, 108, 104, 105),
        (105, 106, 100, 101),   # decision LOW
        (101, 105, 101, 104),
        (104, 108, 103, 107),
        (107, 106, 102, 104),   # HIGH2 is pivot high 106
        (104, 103, 99, 99.5),   # close below decision HL -> activation
        (99.5, 101, 98, 100),
    ]
    for i, (o, h, l, c) in enumerate(vals):
        bars.append(Bar(t0 + timedelta(hours=4*i), o, h, l, c, 1))

    h1 = Pivot("HIGH", 1, bars[1].time, 110.0, 2, bars[2].time, 0.38)
    low = Pivot("LOW", 3, bars[3].time, 100.0, 4, bars[4].time, 0.38)
    h2 = Pivot("HIGH", 6, bars[6].time, 106.0, 7, bars[7].time, 0.38)

    cands = build_channel_candidates(bars, [h1, low, h2])
    falling = [c for c in cands if c.direction == "FALLING"]
    assert len(falling) == 1
    c = falling[0]
    assert c.anchor1 is h1
    assert c.anchor2 is h2
    assert c.decision_hl is low
    assert c.hl_break_time == bars[7].time
    assert c.hl_break_mode == "CLOSED_BAR_CLOSE_PROVISIONAL"
    assert hl_activation_event_end_indices_from_pivots(bars, [h1, low, h2]) == [7]

    # Without a post-anchor2 break of the middle LOW, no falling TL may activate.
    unbroken = list(bars)
    unbroken[7] = Bar(unbroken[7].time, 104, 103, 100.2, 100.5, 1)
    assert not [
        x for x in build_channel_candidates(unbroken, [h1, low, h2])
        if x.direction == "FALLING"
    ]
    assert hl_activation_event_end_indices_from_pivots(unbroken, [h1, low, h2]) == []

    print("NVT9 HL-ACTIVATED GEOMETRY SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
