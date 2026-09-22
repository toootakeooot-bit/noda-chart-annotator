from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from live_draw.model import Bar, ChannelCandidate, Pivot
from live_draw.tl_transition import resolve_tl_transition_from_candidates


def make_bars(*, broken: bool) -> list[Bar]:
    t0 = datetime(2026, 9, 1)
    rows = []
    closes = [101.0, 104.0, 103.0, 104.5, 105.0]
    if broken:
        closes[-1] = 100.0
    for i, close in enumerate(closes):
        rows.append(
            Bar(
                t0 + timedelta(hours=i),
                close,
                close + 0.5,
                close - 0.5,
                close,
            )
        )
    return rows


def make_candidate(bars: list[Bar], *, unbroken: bool) -> ChannelCandidate:
    a1 = Pivot(
        "LOW", 0, bars[0].time, 100.0,
        0, bars[0].time, 0.38,
    )
    decision = Pivot(
        "HIGH", 1, bars[1].time, 104.0,
        1, bars[1].time, 0.38,
    )
    a2 = Pivot(
        "LOW", 2, bars[2].time, 102.0,
        2, bars[2].time, 0.38,
    )
    slope = (a2.price - a1.price) / (a2.time - a1.time).total_seconds()
    return ChannelCandidate(
        direction="RISING",
        anchor1=a1,
        anchor2=a2,
        slope_per_second=slope,
        turn_span=3,
        tl_contacts=2,
        ch_contacts=1,
        unbroken_close=unbroken,
        ch_anchor=decision,
        ch_offset=3.0,
        zone_width=0.1,
        decision_hl=decision,
        hl_break_time=bars[3].time,
        hl_break_mode="CLOSED_BAR_CLOSE_PROVISIONAL",
    )


def selected_state(c: ChannelCandidate) -> dict:
    return {
        "direction": c.direction,
        "anchor1_time": c.anchor1.time.isoformat(),
        "anchor1_price": float(c.anchor1.price),
        "anchor2_time": c.anchor2.time.isoformat(),
        "anchor2_price": float(c.anchor2.price),
    }


def main() -> None:
    active_bars = make_bars(broken=False)
    active_c = make_candidate(active_bars, unbroken=True)

    active = resolve_tl_transition_from_candidates(
        active_bars, "USDJPY#", "H1", [active_c], 3, selected_state(active_c)
    )
    assert active.state == "ACTIVE"
    assert active.reason_code == "SELECTED_TL_STILL_UNBROKEN"
    assert active.active_candidate is active_c

    new_active = resolve_tl_transition_from_candidates(
        active_bars, "USDJPY#", "H1", [active_c], 3, None
    )
    assert new_active.state == "NEW_ACTIVE"
    assert new_active.reason_code == "NEW_N_STRUCTURE_CONFIRMED_AND_HL_BROKEN"
    assert new_active.active_candidate is active_c

    broken_bars = make_bars(broken=True)
    broken_c = make_candidate(broken_bars, unbroken=False)
    transition = resolve_tl_transition_from_candidates(
        broken_bars, "USDJPY#", "H4", [broken_c], 3, selected_state(broken_c)
    )
    assert transition.state == "TRANSITION_NO_TL"
    assert transition.reason_code == "OLD_TL_BROKEN_NO_UNBROKEN_REPLACEMENT_N"
    assert transition.active_candidate is None
    assert transition.broken_candidate is broken_c
    assert transition.break_time == broken_bars[-1].time

    empty = resolve_tl_transition_from_candidates(
        active_bars, "USDJPY#", "H4", [], 1, None
    )
    assert empty.state == "TRANSITION_NO_TL"
    assert empty.reason_code == "NO_ACTIVATED_N_STRUCTURE_YET"

    print("TL_TRANSITION_SELFTEST_PASS")


if __name__ == "__main__":
    main()
