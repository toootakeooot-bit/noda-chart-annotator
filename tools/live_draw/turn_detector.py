from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .model import Bar, Pivot

LegDirection = Literal['RISING', 'FALLING']


@dataclass
class TurnDetectorResult:
    pivots: list[Pivot]
    active_leg: LegDirection | None
    active_start_index: int | None
    active_extreme_index: int | None
    active_threshold: float | None
    detector_version: str = '1.0'
    status: str = 'PROVISIONAL'


def _rising_threshold(low: float, high: float, retracement: float) -> float:
    return high - (high - low) * retracement


def _falling_threshold(high: float, low: float, retracement: float) -> float:
    return low + (high - low) * retracement


def detect_turns(bars: list[Bar], retracement: float = 0.38) -> TurnDetectorResult:
    """Detect alternating HIGH/LOW turns using only closed bars.

    A wave extreme becomes a confirmed turn only when a later closed-bar close
    retraces at least 38% of the active small-Dow wave. Wick-only penetration
    does not confirm a turn in detector v1.
    """
    if len(bars) < 3:
        return TurnDetectorResult([], None, None, None, None)

    pivots: list[Pivot] = []
    low_idx = high_idx = 0
    low_price = bars[0].low
    high_price = bars[0].high
    direction: LegDirection | None = None
    start_idx: int | None = None
    extreme_idx: int | None = None

    i = 1
    while i < len(bars) and direction is None:
        b = bars[i]
        if b.low < low_price:
            low_price, low_idx = b.low, i
        if b.high > high_price:
            high_price, high_idx = b.high, i

        if high_idx > low_idx and high_price > low_price:
            threshold = _rising_threshold(low_price, high_price, retracement)
            if i > high_idx and b.close <= threshold:
                pivots.append(Pivot('LOW', low_idx, bars[low_idx].time, low_price, low_idx, bars[low_idx].time, retracement))
                pivots.append(Pivot('HIGH', high_idx, bars[high_idx].time, high_price, i, b.time, retracement))
                direction = 'FALLING'
                start_idx = high_idx
                extreme_idx = min(range(high_idx, i + 1), key=lambda j: bars[j].low)
                break
        if low_idx > high_idx and high_price > low_price:
            threshold = _falling_threshold(high_price, low_price, retracement)
            if i > low_idx and b.close >= threshold:
                pivots.append(Pivot('HIGH', high_idx, bars[high_idx].time, high_price, high_idx, bars[high_idx].time, retracement))
                pivots.append(Pivot('LOW', low_idx, bars[low_idx].time, low_price, i, b.time, retracement))
                direction = 'RISING'
                start_idx = low_idx
                extreme_idx = max(range(low_idx, i + 1), key=lambda j: bars[j].high)
                break
        i += 1

    if direction is None:
        if high_idx > low_idx:
            direction = 'RISING'
            start_idx, extreme_idx = low_idx, high_idx
            threshold = _rising_threshold(low_price, high_price, retracement)
        elif low_idx > high_idx:
            direction = 'FALLING'
            start_idx, extreme_idx = high_idx, low_idx
            threshold = _falling_threshold(high_price, low_price, retracement)
        else:
            threshold = None
        return TurnDetectorResult(pivots, direction, start_idx, extreme_idx, threshold)

    i += 1
    while i < len(bars):
        b = bars[i]
        assert start_idx is not None and extreme_idx is not None
        if direction == 'RISING':
            if b.high > bars[extreme_idx].high:
                extreme_idx = i
            start_low = bars[start_idx].low
            extreme_high = bars[extreme_idx].high
            threshold = _rising_threshold(start_low, extreme_high, retracement)
            if i > extreme_idx and b.close <= threshold:
                pivots.append(Pivot('HIGH', extreme_idx, bars[extreme_idx].time, extreme_high, i, b.time, retracement))
                direction = 'FALLING'
                start_idx = extreme_idx
                extreme_idx = min(range(start_idx, i + 1), key=lambda j: bars[j].low)
        else:
            if b.low < bars[extreme_idx].low:
                extreme_idx = i
            start_high = bars[start_idx].high
            extreme_low = bars[extreme_idx].low
            threshold = _falling_threshold(start_high, extreme_low, retracement)
            if i > extreme_idx and b.close >= threshold:
                pivots.append(Pivot('LOW', extreme_idx, bars[extreme_idx].time, extreme_low, i, b.time, retracement))
                direction = 'RISING'
                start_idx = extreme_idx
                extreme_idx = max(range(start_idx, i + 1), key=lambda j: bars[j].high)
        i += 1

    active_threshold = None
    if start_idx is not None and extreme_idx is not None:
        if direction == 'RISING':
            active_threshold = _rising_threshold(bars[start_idx].low, bars[extreme_idx].high, retracement)
        else:
            active_threshold = _falling_threshold(bars[start_idx].high, bars[extreme_idx].low, retracement)
    return TurnDetectorResult(pivots, direction, start_idx, extreme_idx, active_threshold)
