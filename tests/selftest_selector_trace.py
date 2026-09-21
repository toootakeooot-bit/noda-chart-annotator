from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from live_draw.geometry import select_large_mid
from live_draw.model import ChannelCandidate, Pivot


def pivot(kind: str, day: int, price: float) -> Pivot:
    t = datetime(2026, 1, 1) + timedelta(days=day)
    return Pivot(kind, day, t, price, day + 1, t + timedelta(hours=4), 0.38)


def candidate(
    direction: str,
    a1: Pivot,
    a2: Pivot,
    ch: Pivot,
    *,
    span: int,
    tl: int,
    chn: int,
    slope: float,
    unbroken: bool = True,
) -> ChannelCandidate:
    return ChannelCandidate(
        direction=direction,
        anchor1=a1,
        anchor2=a2,
        slope_per_second=slope,
        turn_span=span,
        tl_contacts=tl,
        ch_contacts=chn,
        unbroken_close=unbroken,
        ch_anchor=ch,
        ch_offset=1.0 if direction == "RISING" else -1.0,
        zone_width=0.1,
    )


def main() -> None:
    l0 = pivot("LOW", 0, 100.0)
    l1 = pivot("LOW", 1, 101.0)
    l2 = pivot("LOW", 2, 102.0)
    l8 = pivot("LOW", 8, 108.0)
    l9 = pivot("LOW", 9, 109.0)
    l10 = pivot("LOW", 10, 110.0)
    h5 = pivot("HIGH", 5, 115.0)

    large_winner = candidate("RISING", l0, l10, h5, span=10, tl=5, chn=7, slope=0.00010)
    large_ch_loser = candidate("RISING", l0, l9, h5, span=10, tl=5, chn=6, slope=0.00005)
    mid_winner = candidate("RISING", l1, l9, h5, span=8, tl=4, chn=5, slope=0.00008)
    mid_older = candidate("RISING", l2, l8, h5, span=7, tl=9, chn=9, slope=0.00001)
    broken = candidate("RISING", l0, l8, h5, span=99, tl=99, chn=99, slope=0.00001, unbroken=False)

    candidates = [large_winner, large_ch_loser, mid_winner, mid_older, broken]

    plain_large, plain_mid, plain_audit = select_large_mid("USDJPY#", "H4", candidates)
    traced_large, traced_mid, traced_audit = select_large_mid(
        "USDJPY#", "H4", candidates, include_trace=True
    )

    assert plain_large is not None and traced_large is not None
    assert plain_mid is not None and traced_mid is not None
    assert plain_large.candidate.id_key == traced_large.candidate.id_key == large_winner.id_key
    assert plain_mid.candidate.id_key == traced_mid.candidate.id_key == mid_winner.id_key
    assert plain_audit["large_reason"] == traced_audit["large_reason"]
    assert plain_audit["mid_reason"] == traced_audit["mid_reason"]

    trace = traced_audit["selector_trace"]
    assert trace["audit_only"] is True
    assert trace["selection_semantics_changed"] is False
    assert trace["large"]["selected_native_candidate_id"] == large_winner.id_key
    assert trace["mid"]["selected_native_candidate_id"] == mid_winner.id_key
    assert trace["large"]["anchor1_pivot_id"].startswith("P-H4-L-")
    assert trace["large"]["selected_candidate_audit_id"].startswith("C-H4-R-")

    large_reasons = {
        row["native_candidate_id"]: row["reason_code"]
        for row in trace["large"]["rejections"]
    }
    assert large_reasons[large_ch_loser.id_key] == "S05_FEWER_CH_CONTACTS"
    assert large_reasons[broken.id_key] == "S06_FILTERED_BROKEN_CLOSE"

    mid_reasons = {
        row["native_candidate_id"]: row["reason_code"]
        for row in trace["mid"]["rejections"]
    }
    assert mid_reasons[mid_older.id_key] == "M04_OLDER_ANCHOR2"

    print("SELECTOR_TRACE_SELFTEST_PASS")


if __name__ == "__main__":
    main()
