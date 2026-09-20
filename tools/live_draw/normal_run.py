from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Iterable

from .geometry import build_channel_candidates, select_large_mid
from .lifecycle import promote_selection
from .market_input import load_ohlc_csv
from .model import Bar
from .turn_detector import detect_turns

TFS = ('D1', 'H4', 'H1', 'M15')


def empty_state() -> dict:
    return {'schema': 'nca-live-state/1.0', 'slots': {}}


def safe_symbol_filename(symbol: str) -> str:
    """Return a Windows/MT4 Common-Files-safe filename fragment.

    The canonical symbol itself is never changed in state/snapshot data. This
    helper is only for filesystem paths.
    """
    symbol = symbol.strip()
    if not symbol:
        raise ValueError('symbol must be non-empty')
    return re.sub(r'[<>:"/\\|?*]+', '_', symbol)


def normal_input_name(symbol: str, timeframe: str) -> str:
    if timeframe not in TFS:
        raise ValueError(f'unsupported timeframe: {timeframe}')
    return f'NORMAL_{safe_symbol_filename(symbol)}_{timeframe}.csv'


def structural_event_end_indices(bars: list[Bar]) -> list[int]:
    """Return closed-bar indices where confirmed Turn information changes.

    Normal Run lifecycle generations are allowed to advance only on structural
    confirmation, not on every ordinary closed bar.  The full closed-bar Turn
    detector already records the bar index that confirmed each pivot.  Replaying
    only those confirmation points preserves chronological reconstruction while
    avoiding repeated expensive channel-candidate generation on bars that cannot
    create a new TL generation under Lifecycle v1.
    """
    if len(bars) < 3:
        return []
    turns = detect_turns(bars)
    indices = {
        int(p.confirmed_by_index)
        for p in turns.pivots
        if 2 <= int(p.confirmed_by_index) < len(bars)
    }
    return sorted(indices)


def hl_activation_event_end_indices_from_pivots(
    bars: list[Bar],
    pivots: list,
) -> list[int]:
    """Return lifecycle event indices for candidate decision-HL crossings."""
    candidates = build_channel_candidates(bars, pivots)
    time_to_index = {bar.time: i for i, bar in enumerate(bars)}
    indices = set()
    for candidate in candidates:
        t = candidate.hl_break_time
        if t is None:
            continue
        idx = time_to_index.get(t)
        if idx is None or idx < 2 or idx >= len(bars):
            continue
        # The candidate cannot become actionable before all three structural
        # pivots used by the N are confirmed.
        confirmed_idx = max(
            int(candidate.anchor1.confirmed_by_index),
            int(candidate.anchor2.confirmed_by_index),
            int(candidate.decision_hl.confirmed_by_index) if candidate.decision_hl else 0,
        )
        if idx < confirmed_idx:
            continue
        indices.add(idx)
    return sorted(indices)


def hl_activation_event_end_indices(bars: list[Bar]) -> list[int]:
    """Return closed-bar indices where an N-structure decision HL is crossed.

    A TL candidate can become eligible *after* its anchor2 pivot was already
    confirmed. Such an HL-break bar may not confirm a new Pivot, so replaying
    Pivot-confirmation events alone can leave an obsolete TL active until the
    next Turn.

    This function schedules those first HL-break closes as lifecycle events.
    The later prefix rebuild still uses only bars available through each event,
    preserving no-lookahead behavior.
    """
    if len(bars) < 3:
        return []
    turns = detect_turns(bars)
    return hl_activation_event_end_indices_from_pivots(bars, turns.pivots)


def lifecycle_event_end_indices(bars: list[Bar]) -> tuple[list[int], list[int], list[int]]:
    """Return (all, pivot-confirmation, HL-activation) replay event indices."""
    pivot_events = structural_event_end_indices(bars)
    hl_events = hl_activation_event_end_indices(bars)
    return sorted(set(pivot_events) | set(hl_events)), pivot_events, hl_events


def rebuild_timeframe_from_bars(
    bars: list[Bar],
    symbol: str,
    timeframe: str,
) -> tuple[dict, dict]:
    """Rebuild TL generations chronologically at confirmed structural events.

    Every Normal Run starts from an empty lifecycle state.  Closed-bar history
    is still authoritative, but expensive detector/candidate/selector replay is
    performed only at confirmed-Turn event points.  Ordinary bars between those
    events cannot by themselves create a replacement TL under Lifecycle v1.

    This keeps `previous` as the true immediately prior reconstructed TL while
    avoiding the original O(600-prefix) repeated candidate-generation path.
    """
    if timeframe not in TFS:
        raise ValueError(f'unsupported timeframe: {timeframe}')
    if not symbol.strip():
        raise ValueError('symbol must be non-empty')
    if len(bars) < 3:
        raise ValueError('at least 3 closed bars are required')

    state = empty_state()
    transitions: list[dict] = []
    event_indices, pivot_event_indices, hl_event_indices = lifecycle_event_end_indices(bars)
    pivot_event_set = set(pivot_event_indices)
    hl_event_set = set(hl_event_indices)
    evaluated_prefixes = 0
    final_event_detector = None
    final_classifier = None
    final_candidate_count = 0
    last_event_end_index = None

    for end_index in event_indices:
        prefix = bars[:end_index + 1]
        turns = detect_turns(prefix)
        candidates = build_channel_candidates(prefix, turns.pivots)
        large, mid, class_audit = select_large_mid(symbol, timeframe, candidates)
        evaluated_prefixes += 1
        last_event_end_index = end_index

        for selected in (large, mid):
            if selected is None:
                continue
            state, did_change = promote_selection(state, selected)
            if did_change:
                key = f'{selected.symbol}|{selected.timeframe}|{selected.level}'
                slot = state['slots'][key]
                event_kinds = []
                if end_index in pivot_event_set:
                    event_kinds.append('PIVOT_CONFIRMATION')
                if end_index in hl_event_set:
                    event_kinds.append('HL_ACTIVATION')
                transitions.append({
                    'closed_bar_time': prefix[-1].time.isoformat(),
                    'closed_bar_index': end_index,
                    'event_kinds': event_kinds,
                    'level': selected.level,
                    'generation': slot['current']['generation'],
                    'line_id': slot['current']['line_id'],
                    'candidate_id': selected.candidate.id_key,
                    'decision_hl_time': (
                        selected.candidate.decision_hl.time.isoformat()
                        if selected.candidate.decision_hl else None
                    ),
                    'decision_hl_price': (
                        float(selected.candidate.decision_hl.price)
                        if selected.candidate.decision_hl else None
                    ),
                    'hl_break_time': (
                        selected.candidate.hl_break_time.isoformat()
                        if selected.candidate.hl_break_time else None
                    ),
                })

        final_event_detector = turns
        final_classifier = class_audit
        final_candidate_count = len(candidates)

    # Full-history detector is cheap compared with channel candidate generation
    # and is useful audit evidence even when the last structural event occurred
    # before the final exported bar.
    full_detector = detect_turns(bars)

    if not event_indices:
        # No confirmed structural event means no TL generation can be rebuilt.
        final_event_detector = full_detector
        final_classifier = None
        final_candidate_count = 0

    audit = {
        'status': 'PASS',
        'mode': 'NORMAL_RUN_HISTORY_REBUILD',
        'replay_strategy': 'PIVOT_CONFIRMATION_PLUS_HL_ACTIVATION',
        'symbol': symbol,
        'timeframe': timeframe,
        'closed_bars': len(bars),
        'structural_event_count': len(event_indices),
        'pivot_confirmation_event_count': len(pivot_event_indices),
        'hl_activation_event_count': len(hl_event_indices),
        'event_indices': event_indices,
        'pivot_confirmation_event_indices': pivot_event_indices,
        'hl_activation_event_indices': hl_event_indices,
        'evaluated_prefixes': evaluated_prefixes,
        'skipped_non_structural_prefixes': max(0, (len(bars) - 2) - evaluated_prefixes),
        'last_structural_event_index': last_event_end_index,
        'last_structural_event_time': (
            bars[last_event_end_index].time.isoformat() if last_event_end_index is not None else None
        ),
        'transition_count': len(transitions),
        'transitions': transitions,
        'full_history_detector': {
            'version': full_detector.detector_version,
            'status': full_detector.status,
            'confirmed_turns': len(full_detector.pivots),
            'active_leg': full_detector.active_leg,
            'active_threshold': full_detector.active_threshold,
        },
        'last_event_detector': {
            'version': final_event_detector.detector_version,
            'status': final_event_detector.status,
            'confirmed_turns': len(final_event_detector.pivots),
            'active_leg': final_event_detector.active_leg,
            'active_threshold': final_event_detector.active_threshold,
        },
        'last_event_geometry': {
            'candidate_count': final_candidate_count,
            'classifier': final_classifier,
        },
    }
    return state, audit


def rebuild_timeframe_from_csv(
    input_csv: str | Path,
    symbol: str,
    timeframe: str,
) -> tuple[dict, dict]:
    bars = load_ohlc_csv(input_csv)
    return rebuild_timeframe_from_bars(bars, symbol, timeframe)


def merge_rebuilt_states(states: Iterable[dict]) -> dict:
    merged = empty_state()
    for state in states:
        if state.get('schema') != 'nca-live-state/1.0':
            raise ValueError('unexpected state schema')
        for key, slot in state.get('slots', {}).items():
            if key in merged['slots']:
                raise ValueError(f'duplicate rebuilt state slot: {key}')
            merged['slots'][key] = slot
    return merged


def validate_rebuilt_state(state: dict, expected_symbol: str) -> dict:
    if state.get('schema') != 'nca-live-state/1.0':
        raise ValueError('unexpected state schema')
    slots = state.get('slots')
    if not isinstance(slots, dict):
        raise ValueError('state slots must be a dictionary')

    current_count = 0
    previous_count = 0
    for key, slot in slots.items():
        for role in ('current', 'previous'):
            item = slot.get(role)
            if item is None:
                continue
            if item.get('symbol') != expected_symbol:
                raise ValueError(f'symbol mismatch in {key}: {item.get("symbol")}')
            if item.get('timeframe') not in TFS:
                raise ValueError(f'bad timeframe in {key}: {item.get("timeframe")}')
            for p in ('anchor1_price', 'anchor2_price', 'ch_offset', 'zone_width'):
                value = float(item[p])
                if not math.isfinite(value):
                    raise ValueError(f'non-finite {p} in {key}')
            if role == 'current':
                current_count += 1
            else:
                previous_count += 1

    if current_count == 0:
        raise ValueError('history rebuild produced no current TL state')

    return {
        'status': 'PASS',
        'slot_count': len(slots),
        'current_count': current_count,
        'previous_count': previous_count,
    }
