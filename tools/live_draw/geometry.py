from __future__ import annotations

from datetime import datetime
from math import fabs

from .model import Bar, ChannelCandidate, Pivot, SelectedStructure


def line_value(t: datetime, t1: datetime, p1: float, slope_per_second: float) -> float:
    return p1 + (t - t1).total_seconds() * slope_per_second


def _slope(a: Pivot, b: Pivot) -> float:
    dt = (b.time - a.time).total_seconds()
    if dt <= 0:
        raise ValueError('Anchor times must increase')
    return (b.price - a.price) / dt


def _turn_span(pivots: list[Pivot], a: Pivot, b: Pivot) -> int:
    ia = pivots.index(a)
    ib = pivots.index(b)
    return ib - ia + 1


def _pivot_contact(p: Pivot, bars: list[Bar], t1: datetime, p1: float, slope: float, offset: float = 0.0) -> bool:
    bar = bars[p.bar_index]
    y = line_value(p.time, t1, p1, slope) + offset
    return bar.low <= y <= bar.high


def _is_unbroken_close(direction: str, bars: list[Bar], a: Pivot, b: Pivot, slope: float) -> bool:
    """Provisional closed-bar evidence for R07-style unbroken selection.

    This is not the final TL lifecycle break detector. It only records whether
    a CLOSED BAR CLOSE crossed the TL after anchor2 existed.
    """
    for bar in bars[b.bar_index + 1:]:
        y = line_value(bar.time, a.time, a.price, slope)
        if direction == 'RISING' and bar.close < y:
            return False
        if direction == 'FALLING' and bar.close > y:
            return False
    return True


def _zone_width(direction: str, bar: Bar) -> float:
    if direction == 'RISING':
        return max(0.0, min(bar.open, bar.close) - bar.low)
    return max(0.0, bar.high - max(bar.open, bar.close))


def build_channel_candidates(bars: list[Bar], pivots: list[Pivot]) -> list[ChannelCandidate]:
    candidates: list[ChannelCandidate] = []
    lows = [p for p in pivots if p.kind == 'LOW']
    highs = [p for p in pivots if p.kind == 'HIGH']

    def build(direction: str, same: list[Pivot], opposite: list[Pivot]) -> None:
        for i in range(len(same) - 1):
            for j in range(i + 1, len(same)):
                a, b = same[i], same[j]
                if direction == 'RISING' and not (b.price > a.price):
                    continue
                if direction == 'FALLING' and not (b.price < a.price):
                    continue
                slope = _slope(a, b)
                valid_opp = [p for p in opposite if p.time >= a.time]
                if not valid_opp:
                    continue

                tl_contacts = sum(_pivot_contact(p, bars, a.time, a.price, slope) for p in same if p.time >= a.time)

                best_ch = None
                best_key = None
                for ch_anchor in valid_opp:
                    base_y = line_value(ch_anchor.time, a.time, a.price, slope)
                    offset = ch_anchor.price - base_y
                    if direction == 'RISING' and offset <= 0:
                        continue
                    if direction == 'FALLING' and offset >= 0:
                        continue
                    ch_contacts = sum(
                        _pivot_contact(p, bars, a.time, a.price, slope, offset)
                        for p in opposite if p.time >= a.time
                    )
                    # No weighted strength score: lexicographic evidence only.
                    key = (ch_contacts, ch_anchor.time)
                    if best_key is None or key > best_key:
                        best_key = key
                        best_ch = (ch_anchor, offset, ch_contacts)
                if best_ch is None:
                    continue

                ch_anchor, offset, ch_contacts = best_ch
                candidates.append(
                    ChannelCandidate(
                        direction=direction,
                        anchor1=a,
                        anchor2=b,
                        slope_per_second=slope,
                        turn_span=_turn_span(pivots, a, b),
                        tl_contacts=tl_contacts,
                        ch_contacts=ch_contacts,
                        unbroken_close=_is_unbroken_close(direction, bars, a, b, slope),
                        ch_anchor=ch_anchor,
                        ch_offset=offset,
                        zone_width=_zone_width(direction, bars[a.bar_index]),
                    )
                )

    build('RISING', lows, highs)
    build('FALLING', highs, lows)
    return candidates


def _gentler(c: ChannelCandidate) -> float:
    return -fabs(c.slope_per_second)


def select_large_mid(symbol: str, timeframe: str, candidates: list[ChannelCandidate]) -> tuple[SelectedStructure | None, SelectedStructure | None, dict]:
    """Provisional relative structure classifier and in-process TL selector.

    No timeframe->Dow mapping and no weighted score is used.
    LARGE_DOW: close-unbroken after anchor2, larger relative turn scope, then
    CH/TL direct-contact evidence, then gentler slope as tie-break only.
    MID_DOW: structurally smaller/recent candidate inside the active large
    context; direction may differ.
    """
    audit = {
        'classifier_version': 'PROVISIONAL_RELATIVE_STRUCTURE_0.1',
        'candidate_count': len(candidates),
        'large_reason': None,
        'mid_reason': None,
    }
    if not candidates:
        return None, None, audit

    large_pool = [c for c in candidates if c.unbroken_close]
    if not large_pool:
        audit['large_reason'] = 'NO_UNBROKEN_CANDIDATE'
        return None, None, audit

    large_c = max(large_pool, key=lambda c: (c.turn_span, c.ch_contacts, c.tl_contacts, _gentler(c)))
    large = SelectedStructure(symbol, timeframe, 'LARGE_DOW', large_c)
    audit['large_reason'] = {
        'turn_span': large_c.turn_span,
        'ch_contacts': large_c.ch_contacts,
        'tl_contacts': large_c.tl_contacts,
        'unbroken_close': large_c.unbroken_close,
        'tie_break': 'GENTLER_SLOPE_ONLY_WHEN_OTHERWISE_COMPARABLE',
    }

    mid_pool = [
        c for c in candidates
        if c.id_key != large_c.id_key
        and c.anchor1.time >= large_c.anchor1.time
        and c.turn_span < large_c.turn_span
    ]
    mid = None
    if mid_pool:
        mid_c = max(mid_pool, key=lambda c: (c.anchor2.time, c.ch_contacts, c.tl_contacts, _gentler(c)))
        mid = SelectedStructure(symbol, timeframe, 'MID_DOW', mid_c)
        audit['mid_reason'] = {
            'inside_large_context_from': large_c.anchor1.time.isoformat(),
            'turn_span': mid_c.turn_span,
            'ch_contacts': mid_c.ch_contacts,
            'tl_contacts': mid_c.tl_contacts,
            'direction_may_differ_from_large': True,
        }
    else:
        audit['mid_reason'] = 'NO_SMALLER_RECENT_CANDIDATE'

    return large, mid, audit


def structure_lines(s: SelectedStructure) -> dict[str, tuple[datetime, float, datetime, float]]:
    c = s.candidate
    t1, t2 = c.anchor1.time, c.anchor2.time
    tl1, tl2 = c.anchor1.price, c.anchor2.price
    ch1, ch2 = tl1 + c.ch_offset, tl2 + c.ch_offset

    if c.direction == 'RISING':
        tlz1, tlz2 = tl1 + c.zone_width, tl2 + c.zone_width
        chz1, chz2 = ch1 - c.zone_width, ch2 - c.zone_width
    else:
        tlz1, tlz2 = tl1 - c.zone_width, tl2 - c.zone_width
        chz1, chz2 = ch1 + c.zone_width, ch2 + c.zone_width

    return {
        'TL': (t1, tl1, t2, tl2),
        'CH': (t1, ch1, t2, ch2),
        'TL_ZONE_EDGE': (t1, tlz1, t2, tlz2),
        'CH_ZONE_EDGE': (t1, chz1, t2, chz2),
    }
