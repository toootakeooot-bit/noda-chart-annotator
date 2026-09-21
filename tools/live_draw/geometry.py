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

                # The TL anchors must form one structural N with a decision HL
                # between them. For FALLING use the lowest confirmed LOW
                # between HIGH1/HIGH2; for RISING use the highest confirmed HIGH
                # between LOW1/LOW2.
                between_opp = [p for p in opposite if a.time < p.time < b.time]
                if not between_opp:
                    continue
                if direction == 'FALLING':
                    decision_hl = min(between_opp, key=lambda p: (p.price, p.time))
                else:
                    decision_hl = max(between_opp, key=lambda p: (p.price, p.time))

                # Research activation rule: after anchor2 formed, a CLOSED-BAR
                # close must cross the decision HL before the new-direction TL
                # becomes eligible. Wick-vs-close semantics remain provisional
                # until video validation; closed-bar close is used because the
                # existing Turn detector is also close-confirmed.
                hl_break_bar = None
                for bar in bars[b.bar_index + 1:]:
                    if direction == 'FALLING' and bar.close < decision_hl.price:
                        hl_break_bar = bar
                        break
                    if direction == 'RISING' and bar.close > decision_hl.price:
                        hl_break_bar = bar
                        break
                if hl_break_bar is None:
                    continue

                tl_contacts = sum(
                    _pivot_contact(p, bars, a.time, a.price, slope)
                    for p in same if p.time >= a.time
                )

                # The opposite side of this N is the same decision HL used to
                # activate the TL, so use it as the canonical CH anchor.
                ch_anchor = decision_hl
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
                        decision_hl=decision_hl,
                        hl_break_time=hl_break_bar.time,
                        hl_break_mode='CLOSED_BAR_CLOSE_PROVISIONAL',
                    )
                )

    build('RISING', lows, highs)
    build('FALLING', highs, lows)
    return candidates


def _gentler(c: ChannelCandidate) -> float:
    return -fabs(c.slope_per_second)


def _pivot_key(p: Pivot) -> tuple:
    return (p.kind, p.time, float(p.price))


def _build_selector_trace_index(timeframe: str, candidates: list[ChannelCandidate]) -> tuple[dict, dict, list[dict], list[dict]]:
    """Build deterministic audit-only Pivot/Candidate numbering.

    The numbering is derived from the already-generated candidate set and never
    participates in candidate generation, ranking, lifecycle, or rendering.
    """
    pivot_values: dict[tuple, Pivot] = {}
    for c in candidates:
        for p in (c.anchor1, c.anchor2, c.ch_anchor):
            pivot_values[_pivot_key(p)] = p

    pivot_ids: dict[tuple, str] = {}
    pivot_rows: list[dict] = []
    for kind in ("LOW", "HIGH"):
        rows = sorted(
            ((k, p) for k, p in pivot_values.items() if p.kind == kind),
            key=lambda item: (item[1].time, float(item[1].price)),
        )
        kind_code = "L" if kind == "LOW" else "H"
        for no, (key, p) in enumerate(rows, start=1):
            audit_id = f"P-{timeframe}-{kind_code}-{no:03d}"
            pivot_ids[key] = audit_id
            pivot_rows.append({
                "pivot_audit_id": audit_id,
                "pivot_no": no,
                "kind": p.kind,
                "time": p.time.isoformat(),
                "price": float(p.price),
                "confirmed_by_time": p.confirmed_by_time.isoformat(),
                "confirmation_threshold": float(p.retracement),
                "reason_code": "P01_CONFIRMED_BY_RETRACEMENT_THRESHOLD",
            })

    ordered = sorted(
        candidates,
        key=lambda c: (
            c.direction,
            c.anchor1.time,
            c.anchor2.time,
            c.ch_anchor.time,
            float(c.ch_offset),
            float(c.zone_width),
        ),
    )
    candidate_ids: dict[int, str] = {}
    candidate_rows: list[dict] = []
    seq = {"RISING": 0, "FALLING": 0}
    for c in ordered:
        seq[c.direction] += 1
        d = "R" if c.direction == "RISING" else "F"
        audit_id = f"C-{timeframe}-{d}-{seq[c.direction]:04d}"
        candidate_ids[id(c)] = audit_id
        candidate_rows.append({
            "candidate_audit_id": audit_id,
            "native_candidate_id": c.id_key,
            "direction": c.direction,
            "anchor1_pivot_id": pivot_ids[_pivot_key(c.anchor1)],
            "anchor2_pivot_id": pivot_ids[_pivot_key(c.anchor2)],
            "channel_anchor_pivot_id": pivot_ids[_pivot_key(c.ch_anchor)],
            "turn_span": int(c.turn_span),
            "tl_contacts": int(c.tl_contacts),
            "ch_contacts": int(c.ch_contacts),
            "unbroken_close": bool(c.unbroken_close),
            "slope_per_second": float(c.slope_per_second),
            "ch_offset": float(c.ch_offset),
            "zone_width": float(c.zone_width),
        })

    return pivot_ids, candidate_ids, pivot_rows, candidate_rows


def _large_rejection_reason(winner: ChannelCandidate, loser: ChannelCandidate) -> str:
    if not loser.unbroken_close:
        return "S06_FILTERED_BROKEN_CLOSE"
    if loser.turn_span != winner.turn_span:
        return "S03_LOWER_TURN_SPAN"
    if loser.ch_contacts != winner.ch_contacts:
        return "S05_FEWER_CH_CONTACTS"
    if loser.tl_contacts != winner.tl_contacts:
        return "S04_FEWER_TL_CONTACTS"
    if fabs(loser.slope_per_second) != fabs(winner.slope_per_second):
        return "S07_STEEPER_SLOPE_TIEBREAK"
    return "S08_EQUAL_RANK_KEY_INPUT_ORDER"


def _mid_rejection_reason(large_c: ChannelCandidate, winner: ChannelCandidate | None, loser: ChannelCandidate) -> str:
    if loser.id_key == large_c.id_key:
        return "M01_SAME_CANDIDATE_AS_LARGE"
    if loser.anchor1.time < large_c.anchor1.time:
        return "M02_OUTSIDE_LARGE_CONTEXT"
    if loser.turn_span >= large_c.turn_span:
        return "M03_NOT_SMALLER_THAN_LARGE"
    if winner is None:
        return "M00_NO_MID_WINNER"
    if loser.anchor2.time != winner.anchor2.time:
        return "M04_OLDER_ANCHOR2"
    if loser.ch_contacts != winner.ch_contacts:
        return "M05_FEWER_CH_CONTACTS"
    if loser.tl_contacts != winner.tl_contacts:
        return "M06_FEWER_TL_CONTACTS"
    if fabs(loser.slope_per_second) != fabs(winner.slope_per_second):
        return "M07_STEEPER_SLOPE_TIEBREAK"
    return "M08_EQUAL_RANK_KEY_INPUT_ORDER"


def select_large_mid(
    symbol: str,
    timeframe: str,
    candidates: list[ChannelCandidate],
    include_trace: bool = False,
) -> tuple[SelectedStructure | None, SelectedStructure | None, dict]:
    """Provisional relative structure classifier and in-process TL selector.

    Selection semantics are unchanged. include_trace only adds deterministic
    audit metadata explaining the already-existing lexicographic selection.
    """
    audit = {
        'classifier_version': 'PROVISIONAL_RELATIVE_STRUCTURE_0.1',
        'candidate_count': len(candidates),
        'large_reason': None,
        'mid_reason': None,
    }
    pivot_ids = candidate_ids = None
    if include_trace:
        pivot_ids, candidate_ids, pivot_rows, candidate_rows = _build_selector_trace_index(timeframe, candidates)
        audit['selector_trace'] = {
            'schema': 'nca-selector-trace/1.0',
            'audit_id': 'ID10IQ200',
            'audit_only': True,
            'selection_semantics_changed': False,
            'timeframe': timeframe,
            'pivot_count': len(pivot_rows),
            'candidate_count': len(candidate_rows),
            'pivots': pivot_rows,
            'candidate_catalog': candidate_rows,
            'large': None,
            'mid': None,
        }

    if not candidates:
        return None, None, audit

    large_pool = [c for c in candidates if c.unbroken_close]
    if not large_pool:
        audit['large_reason'] = 'NO_UNBROKEN_CANDIDATE'
        if include_trace:
            audit['selector_trace']['large'] = {
                'selected_candidate_audit_id': None,
                'priority_order': ['unbroken_close', 'turn_span', 'ch_contacts', 'tl_contacts', 'gentler_slope'],
                'rejections': [
                    {
                        'candidate_audit_id': candidate_ids[id(c)],
                        'reason_code': 'S06_FILTERED_BROKEN_CLOSE',
                    }
                    for c in candidates
                ],
            }
        return None, None, audit

    # DO NOT change this key: it is the frozen 09/19 selection semantics.
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
    mid_c = None
    if mid_pool:
        # DO NOT change this key: it is the frozen 09/19 selection semantics.
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

    if include_trace:
        trace = audit['selector_trace']
        trace['large'] = {
            'selector_id': f'S-{timeframe}-LARGE',
            'selected_candidate_audit_id': candidate_ids[id(large_c)],
            'selected_native_candidate_id': large_c.id_key,
            'anchor1_pivot_id': pivot_ids[_pivot_key(large_c.anchor1)],
            'anchor2_pivot_id': pivot_ids[_pivot_key(large_c.anchor2)],
            'priority_order': ['unbroken_close', 'turn_span', 'ch_contacts', 'tl_contacts', 'gentler_slope'],
            'selected_metrics': {
                'turn_span': int(large_c.turn_span),
                'ch_contacts': int(large_c.ch_contacts),
                'tl_contacts': int(large_c.tl_contacts),
                'unbroken_close': bool(large_c.unbroken_close),
                'absolute_slope_per_second': float(fabs(large_c.slope_per_second)),
            },
            'rejections': [
                {
                    'candidate_audit_id': candidate_ids[id(c)],
                    'native_candidate_id': c.id_key,
                    'reason_code': _large_rejection_reason(large_c, c),
                }
                for c in candidates if c is not large_c
            ],
        }
        trace['mid'] = {
            'selector_id': f'S-{timeframe}-MID',
            'selected_candidate_audit_id': candidate_ids[id(mid_c)] if mid_c is not None else None,
            'selected_native_candidate_id': mid_c.id_key if mid_c is not None else None,
            'anchor1_pivot_id': pivot_ids[_pivot_key(mid_c.anchor1)] if mid_c is not None else None,
            'anchor2_pivot_id': pivot_ids[_pivot_key(mid_c.anchor2)] if mid_c is not None else None,
            'priority_order': ['inside_large_context', 'smaller_turn_span', 'anchor2_recency', 'ch_contacts', 'tl_contacts', 'gentler_slope'],
            'selected_metrics': ({
                'anchor2_time': mid_c.anchor2.time.isoformat(),
                'turn_span': int(mid_c.turn_span),
                'ch_contacts': int(mid_c.ch_contacts),
                'tl_contacts': int(mid_c.tl_contacts),
                'absolute_slope_per_second': float(fabs(mid_c.slope_per_second)),
            } if mid_c is not None else None),
            'rejections': [
                {
                    'candidate_audit_id': candidate_ids[id(c)],
                    'native_candidate_id': c.id_key,
                    'reason_code': _mid_rejection_reason(large_c, mid_c, c),
                }
                for c in candidates if c is not mid_c
            ],
        }

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
