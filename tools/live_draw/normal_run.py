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


def rebuild_timeframe_from_bars(
    bars: list[Bar],
    symbol: str,
    timeframe: str,
) -> tuple[dict, dict]:
    """Chronologically rebuild TL generations from closed-bar history.

    The rebuild starts from an empty lifecycle state on every Normal Run. Each
    historical closed-bar prefix is evaluated in chronological order using the
    existing detector / selector. This makes `previous` the generation that
    actually preceded the final `current` under the current NCA logic, rather
    than the TL that merely happened to be persisted by the prior run.

    This deliberately favors correctness and auditability over speed for v1.
    """
    if timeframe not in TFS:
        raise ValueError(f'unsupported timeframe: {timeframe}')
    if not symbol.strip():
        raise ValueError('symbol must be non-empty')
    if len(bars) < 3:
        raise ValueError('at least 3 closed bars are required')

    state = empty_state()
    transitions: list[dict] = []
    evaluated_prefixes = 0
    final_detector = None
    final_classifier = None
    final_candidate_count = 0

    for end in range(3, len(bars) + 1):
        prefix = bars[:end]
        turns = detect_turns(prefix)
        candidates = build_channel_candidates(prefix, turns.pivots)
        large, mid, class_audit = select_large_mid(symbol, timeframe, candidates)
        evaluated_prefixes += 1

        for selected in (large, mid):
            if selected is None:
                continue
            state, did_change = promote_selection(state, selected)
            if did_change:
                key = f'{selected.symbol}|{selected.timeframe}|{selected.level}'
                slot = state['slots'][key]
                transitions.append({
                    'closed_bar_time': prefix[-1].time.isoformat(),
                    'level': selected.level,
                    'generation': slot['current']['generation'],
                    'line_id': slot['current']['line_id'],
                    'candidate_id': selected.candidate.id_key,
                })

        if end == len(bars):
            final_detector = turns
            final_classifier = class_audit
            final_candidate_count = len(candidates)

    assert final_detector is not None
    audit = {
        'status': 'PASS',
        'mode': 'NORMAL_RUN_HISTORY_REBUILD',
        'symbol': symbol,
        'timeframe': timeframe,
        'closed_bars': len(bars),
        'evaluated_prefixes': evaluated_prefixes,
        'transition_count': len(transitions),
        'transitions': transitions,
        'final_detector': {
            'version': final_detector.detector_version,
            'status': final_detector.status,
            'confirmed_turns': len(final_detector.pivots),
            'active_leg': final_detector.active_leg,
            'active_threshold': final_detector.active_threshold,
        },
        'final_geometry': {
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
