from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Reuse production live_draw modules without modifying their behavior.
TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from live_draw.geometry import build_channel_candidates, select_large_mid  # noqa: E402
from live_draw.market_input import load_ohlc_csv  # noqa: E402
from live_draw.model import Bar, Pivot  # noqa: E402
from live_draw.normal_run import TFS  # noqa: E402
from live_draw.turn_detector import detect_turns  # noqa: E402


def parse_cutoff(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return datetime.fromisoformat(value)


def bar_morphology(bar: Bar, pivot_kind: str) -> dict:
    total_range = max(0.0, bar.high - bar.low)
    body = abs(bar.close - bar.open)
    upper_wick = max(0.0, bar.high - max(bar.open, bar.close))
    lower_wick = max(0.0, min(bar.open, bar.close) - bar.low)
    relevant_wick = lower_wick if pivot_kind == 'LOW' else upper_wick
    return {
        'range': total_range,
        'body': body,
        'upper_wick': upper_wick,
        'lower_wick': lower_wick,
        'relevant_wick': relevant_wick,
        'relevant_wick_fraction': (relevant_wick / total_range if total_range > 0 else 0.0),
    }


def pivot_payload(p: Pivot, bars: list[Bar]) -> dict:
    bar = bars[p.bar_index]
    return {
        'kind': p.kind,
        'bar_index': p.bar_index,
        'time': p.time.isoformat(),
        'price': p.price,
        'confirmed_by_index': p.confirmed_by_index,
        'confirmed_by_time': p.confirmed_by_time.isoformat(),
        'retracement': p.retracement,
        'candle': bar_morphology(bar, p.kind),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description='NVT2 - dump full NCA candidate pool at a frozen cutoff')
    ap.add_argument('--input-csv', required=True)
    ap.add_argument('--symbol', required=True)
    ap.add_argument('--timeframe', required=True, choices=TFS)
    ap.add_argument('--output', required=True)
    ap.add_argument('--cutoff', help='Optional ISO-8601 bar-time cutoff; bars after this time are excluded')
    args = ap.parse_args()

    symbol = args.symbol.strip()
    if not symbol:
        raise ValueError('symbol must be non-empty')

    bars = load_ohlc_csv(args.input_csv)
    cutoff = parse_cutoff(args.cutoff)
    if cutoff is not None:
        # MT4 source timestamps are normally naive broker times.  A naive cutoff
        # must therefore be compared to naive bars; offset-aware input requires
        # offset-aware bars and is rejected rather than silently converted.
        if bars and (bars[0].time.tzinfo is None) != (cutoff.tzinfo is None):
            raise ValueError('cutoff timezone awareness must match OHLC timestamps')
        bars = [b for b in bars if b.time <= cutoff]

    if len(bars) < 3:
        raise ValueError('at least 3 closed bars are required after cutoff')

    turns = detect_turns(bars)
    candidates = build_channel_candidates(bars, turns.pivots)
    large, mid, classifier_audit = select_large_mid(symbol, args.timeframe, candidates)
    large_id = large.candidate.id_key if large else None
    mid_id = mid.candidate.id_key if mid else None

    rows = []
    for c in candidates:
        rows.append({
            'candidate_id': c.id_key,
            'direction': c.direction,
            'anchor1': pivot_payload(c.anchor1, bars),
            'anchor2': pivot_payload(c.anchor2, bars),
            'ch_anchor': pivot_payload(c.ch_anchor, bars),
            'slope_per_second': c.slope_per_second,
            'absolute_slope_per_second': abs(c.slope_per_second),
            'turn_span': c.turn_span,
            'tl_contacts': c.tl_contacts,
            'ch_contacts': c.ch_contacts,
            'unbroken_close': c.unbroken_close,
            'ch_offset': c.ch_offset,
            'zone_width': c.zone_width,
            'selected_as_large': c.id_key == large_id,
            'selected_as_mid': c.id_key == mid_id,
        })

    payload = {
        'schema': 'nvt-candidate-dump/1.0',
        'mode': 'READ_ONLY_RESEARCH',
        'symbol': symbol,
        'timeframe': args.timeframe,
        'source_csv': str(Path(args.input_csv)),
        'requested_cutoff': args.cutoff,
        'effective_last_closed_bar': bars[-1].time.isoformat(),
        'closed_bar_count': len(bars),
        'first_bar_time': bars[0].time.isoformat(),
        'last_bar_time': bars[-1].time.isoformat(),
        'detector': {
            'version': turns.detector_version,
            'status': turns.status,
            'confirmed_turn_count': len(turns.pivots),
            'active_leg': turns.active_leg,
            'active_threshold': turns.active_threshold,
        },
        'candidate_count': len(candidates),
        'selected_large_candidate_id': large_id,
        'selected_mid_candidate_id': mid_id,
        'classifier_audit': classifier_audit,
        'candidates': rows,
        'production_writeback': False,
        'snapshot_writeback': False,
        'mt4_object_writeback': False,
        'trade_authority': False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'status': 'PASS',
        'output': str(out),
        'symbol': symbol,
        'timeframe': args.timeframe,
        'closed_bar_count': len(bars),
        'confirmed_turn_count': len(turns.pivots),
        'candidate_count': len(candidates),
        'selected_large_candidate_id': large_id,
        'selected_mid_candidate_id': mid_id,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
