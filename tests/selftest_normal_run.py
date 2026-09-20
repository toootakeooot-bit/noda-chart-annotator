from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from live_draw.model import Bar
from live_draw.normal_run import (
    rebuild_timeframe_from_bars,
    rebuild_timeframe_baseline_0919_from_bars,
    rebuild_timeframe_direction_switch_experiment,
    safe_symbol_filename,
    structural_event_end_indices,
    hl_activation_event_end_indices,
    lifecycle_event_end_indices,
    validate_rebuilt_state,
)
from run_normal import publish_validated_snapshot, validate_snapshot


def make_bars() -> list[Bar]:
    closes = [
        100, 105, 110, 106, 102, 106,
        112, 108, 104, 108,
        114, 110, 106, 110,
        116, 112, 108, 112,
        118, 113, 109, 114,
        120, 115, 110, 116,
    ]
    t0 = datetime(2026, 1, 1, 0, 0)
    bars = []
    prev = closes[0]
    for i, c in enumerate(closes):
        o = prev
        high = max(o, c) + 0.10
        low = min(o, c) - 0.10
        bars.append(Bar(t0 + timedelta(minutes=15*i), o, high, low, c, 100+i))
        prev = c
    return bars


def main() -> None:
    assert safe_symbol_filename('GOLD#') == 'GOLD#'
    assert safe_symbol_filename('XAU/USD') == 'XAU_USD'

    bars = make_bars()
    pivot_event_indices = structural_event_end_indices(bars)
    hl_event_indices = hl_activation_event_end_indices(bars)
    event_indices, pivots_again, hl_again = lifecycle_event_end_indices(bars)
    assert pivots_again == pivot_event_indices
    assert hl_again == hl_event_indices
    assert event_indices == sorted(set(pivot_event_indices) | set(hl_event_indices))
    state, audit = rebuild_timeframe_from_bars(bars, 'USDJPY#', 'M15')
    validation = validate_rebuilt_state(state, 'USDJPY#')

    old_ab_state, old_ab_audit = rebuild_timeframe_baseline_0919_from_bars(
        bars, 'USDJPY#', 'M15'
    )
    new_ab_state, new_ab_audit = rebuild_timeframe_direction_switch_experiment(
        bars, 'USDJPY#', 'M15'
    )
    old_ab_validation = validate_rebuilt_state(old_ab_state, 'USDJPY#')
    new_ab_validation = validate_rebuilt_state(new_ab_state, 'USDJPY#')
    assert old_ab_audit['selection_mode'] == 'OLD_0919_TURN_SPAN_CONTACT_DISTANCE_PIPELINE'
    assert new_ab_audit['selection_mode'] == 'DIRECTION_SWITCH_ACTIVE_N_V0_1'
    assert new_ab_audit['candidate_geometry_changed'] is False
    assert new_ab_audit['plan_b_changed'] is False
    assert new_ab_audit['color_policy_changed'] is False
    assert old_ab_validation['current_count'] >= 1
    assert new_ab_validation['current_count'] == 1

    assert audit['status'] == 'PASS'
    assert audit['replay_strategy'] == 'PIVOT_CONFIRMATION_PLUS_HL_ACTIVATION'
    assert audit['structural_event_count'] == len(event_indices)
    assert audit['pivot_confirmation_event_count'] == len(pivot_event_indices)
    assert audit['hl_activation_event_count'] == len(hl_event_indices)
    assert audit['event_indices'] == event_indices
    assert audit['evaluated_prefixes'] == len(event_indices)
    assert audit['evaluated_prefixes'] <= len(bars) - 2
    assert validation['current_count'] >= 1

    # Every displayed previous must be the generation immediately before its
    # displayed current in the reconstructed lifecycle sequence.
    for slot in state['slots'].values():
        current = slot.get('current')
        previous = slot.get('previous')
        if current and previous:
            assert int(previous['generation']) + 1 == int(current['generation'])

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        snap = td / 'NORMAL_USDJPY#_live_snapshot.csv'
        pub = publish_validated_snapshot(snap, state, 'USDJPY#')
        chk = validate_snapshot(snap, 'USDJPY#')
        assert pub['status'] == 'PASS'
        assert chk['status'] == 'PASS'
        assert chk['rows'] == pub['rows']

    print('NORMAL_RUN_SELFTEST_PASS')
    print(json.dumps({
        'state_validation': validation,
        'structural_event_count': audit['structural_event_count'],
        'pivot_confirmation_event_count': audit['pivot_confirmation_event_count'],
        'hl_activation_event_count': audit['hl_activation_event_count'],
        'evaluated_prefixes': audit['evaluated_prefixes'],
        'transition_count': audit['transition_count'],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
