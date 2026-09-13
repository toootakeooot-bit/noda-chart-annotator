from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from live_draw.market_input import write_ohlc_csv
from live_draw.model import Bar
from live_draw.pipeline import run_one_timeframe
from live_draw.turn_detector import detect_turns


def make_bars() -> list[Bar]:
    closes = [
        100, 105, 110, 106, 102, 106,
        112, 108, 104, 108,
        114, 110, 106, 110,
        116, 112, 108, 112,
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
    bars = make_bars()
    turns = detect_turns(bars)
    assert len(turns.pivots) >= 8, f'expected >=8 turns, got {len(turns.pivots)}'
    assert all(p.confirmed_by_index >= p.bar_index for p in turns.pivots)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        inp = td / 'USDJPY_M15.csv'
        state = td / 'state.json'
        snap = td / 'snapshot.csv'
        audit = td / 'audit.json'
        write_ohlc_csv(inp, bars)
        result = run_one_timeframe(inp, 'USDJPY', 'M15', state, snap, audit)

        assert result['status'] == 'PASS'
        assert result['turn_detector']['confirmed_turns'] >= 8
        assert result['geometry']['large_selected'] is not None
        assert result['geometry']['mid_selected'] is not None
        assert result['snapshot_rows'] == 8, result['snapshot_rows']
        assert set(result['lifecycle_changed']) == {'LARGE_DOW', 'MID_DOW'}

        st = json.loads(state.read_text(encoding='utf-8'))
        assert st['schema'] == 'nca-live-state/1.0'
        assert len(st['slots']) == 2
        text = snap.read_text(encoding='utf-8')
        for role in ('TL', 'CH', 'TL_ZONE_EDGE', 'CH_ZONE_EDGE'):
            assert role in text

        result2 = run_one_timeframe(inp, 'USDJPY', 'M15', state, snap, audit)
        assert result2['lifecycle_changed'] == []
        assert result2['snapshot_rows'] == 8

        print('LIVE_DRAW_SELFTEST_PASS')
        print(json.dumps(result2, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
