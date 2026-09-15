from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from live_draw.market_input import load_ohlc_csv
from live_draw.turn_detector import detect_turns


def parse_cutoff(value: str) -> datetime:
    value = value.strip()
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return datetime.fromisoformat(value)


def point_meta(bar, kind: str) -> dict:
    body = abs(bar.close - bar.open)
    rng = max(bar.high - bar.low, 0.0)
    if kind == 'HIGH':
        wick = max(0.0, bar.high - max(bar.open, bar.close))
    else:
        wick = max(0.0, min(bar.open, bar.close) - bar.low)
    return {
        'time': bar.time.isoformat(),
        'price': bar.high if kind == 'HIGH' else bar.low,
        'open': bar.open,
        'high': bar.high,
        'low': bar.low,
        'close': bar.close,
        'wick_size': wick,
        'wick_fraction_of_range': (wick / rng) if rng > 0 else 0.0,
        'wick_to_body': (wick / body) if body > 0 else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description='Build research-only nested Micro-Dow candidate pool.')
    ap.add_argument('--input-csv', required=True)
    ap.add_argument('--cutoff', required=True)
    ap.add_argument('--timeframe', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--lookback-bars', type=int, default=360)
    ap.add_argument('--local-radius', type=int, default=2)
    args = ap.parse_args()

    src = Path(args.input_csv)
    source_bars = load_ohlc_csv(src)
    cutoff = parse_cutoff(args.cutoff)
    frozen_all = [b for b in source_bars if b.time <= cutoff]
    if len(frozen_all) < 10:
        raise ValueError('insufficient closed bars at cutoff')

    # Production-equivalent 38% pivots must be computed from the complete frozen
    # history.  The research lookback is applied only to the Micro-Dow lens and
    # output pool; truncating first would change the production detector state.
    turns = detect_turns(frozen_all)

    bars = frozen_all[-max(args.lookback_bars, 10):]
    radius = max(1, args.local_radius)
    first_lookback_time = bars[0].time
    lookback_times = {b.time.isoformat() for b in bars}

    confirmed_high_times = {
        p.time.isoformat() for p in turns.pivots
        if p.kind == 'HIGH' and p.time >= first_lookback_time
    }
    confirmed_low_times = {
        p.time.isoformat() for p in turns.pivots
        if p.kind == 'LOW' and p.time >= first_lookback_time
    }

    def is_local_high(i: int) -> bool:
        if i < radius or i + radius >= len(bars):
            return False
        h = bars[i].high
        return all(h >= bars[j].high for j in range(i - radius, i + radius + 1) if j != i)

    def is_local_low(i: int) -> bool:
        if i < radius or i + radius >= len(bars):
            return False
        lo = bars[i].low
        return all(lo <= bars[j].low for j in range(i - radius, i + radius + 1) if j != i)

    local_high_idx = [i for i in range(len(bars)) if is_local_high(i)]
    local_low_idx = [i for i in range(len(bars)) if is_local_low(i)]

    micro_highs = []
    for i in local_high_idx:
        prev_lows = [j for j in local_low_idx if j < i]
        next_lows = [j for j in local_low_idx if j > i]
        if not prev_lows or not next_lows:
            continue
        p = prev_lows[-1]
        n = next_lows[0]
        if bars[n].low >= bars[p].low:
            continue
        row = point_meta(bars[i], 'HIGH')
        row.update({
            'kind': 'HIGH',
            'index_in_lookback': i,
            'production_confirmed': bars[i].time.isoformat() in confirmed_high_times,
            'micro_rule': 'LOW1 -> rebound HIGH -> LOWER LOW',
            'previous_low_time': bars[p].time.isoformat(),
            'previous_low': bars[p].low,
            'next_low_time': bars[n].time.isoformat(),
            'next_low': bars[n].low,
        })
        micro_highs.append(row)

    micro_lows = []
    for i in local_low_idx:
        prev_highs = [j for j in local_high_idx if j < i]
        next_highs = [j for j in local_high_idx if j > i]
        if not prev_highs or not next_highs:
            continue
        p = prev_highs[-1]
        n = next_highs[0]
        if bars[n].high <= bars[p].high:
            continue
        row = point_meta(bars[i], 'LOW')
        row.update({
            'kind': 'LOW',
            'index_in_lookback': i,
            'production_confirmed': bars[i].time.isoformat() in confirmed_low_times,
            'micro_rule': 'HIGH1 -> pullback LOW -> HIGHER HIGH',
            'previous_high_time': bars[p].time.isoformat(),
            'previous_high': bars[p].high,
            'next_high_time': bars[n].time.isoformat(),
            'next_high': bars[n].high,
        })
        micro_lows.append(row)

    confirmed_highs = []
    confirmed_lows = []
    time_to_bar = {b.time.isoformat(): b for b in bars}
    for p in turns.pivots:
        key = p.time.isoformat()
        if key not in lookback_times or key not in time_to_bar:
            continue
        b = time_to_bar[key]
        row = point_meta(b, p.kind)
        row.update({
            'kind': p.kind,
            'production_index': p.index,
            'production_confirmed': True,
            'confirmed_at': p.confirmed_time.isoformat(),
            'retracement': p.retracement,
        })
        if p.kind == 'HIGH':
            confirmed_highs.append(row)
        else:
            confirmed_lows.append(row)

    def merged_points(confirmed: list[dict], micro: list[dict]) -> list[dict]:
        by_time = {}
        for row in micro:
            r = dict(row)
            r['source_layer'] = 'MICRO_DOW'
            by_time[row['time']] = r
        for row in confirmed:
            r = dict(row)
            r['source_layer'] = 'CONFIRMED_38'
            by_time[row['time']] = r
        return sorted(by_time.values(), key=lambda r: r['time'])

    high_points = merged_points(confirmed_highs, micro_highs)
    low_points = merged_points(confirmed_lows, micro_lows)

    def provenance(a: dict, b: dict) -> str:
        left = 'P38' if a['source_layer'] == 'CONFIRMED_38' else 'MICRO'
        right = 'P38' if b['source_layer'] == 'CONFIRMED_38' else 'MICRO'
        return f'{left}_{right}'

    falling = []
    for ia, a in enumerate(high_points):
        t1 = datetime.fromisoformat(a['time'])
        for b in high_points[ia + 1:]:
            t2 = datetime.fromisoformat(b['time'])
            if float(b['price']) >= float(a['price']):
                continue
            hours = (t2 - t1).total_seconds() / 3600.0
            if hours <= 0:
                continue
            slope = (float(b['price']) - float(a['price'])) / hours
            falling.append({
                'direction': 'FALLING',
                'candidate_key': f"MICROPOOL:FALLING:{a['time']}:{b['time']}",
                'provenance': provenance(a, b),
                'anchor1': a,
                'anchor2': b,
                'elapsed_hours': hours,
                'slope_per_hour': slope,
                'absolute_slope_per_hour': abs(slope),
            })

    rising = []
    for ia, a in enumerate(low_points):
        t1 = datetime.fromisoformat(a['time'])
        for b in low_points[ia + 1:]:
            t2 = datetime.fromisoformat(b['time'])
            if float(b['price']) <= float(a['price']):
                continue
            hours = (t2 - t1).total_seconds() / 3600.0
            if hours <= 0:
                continue
            slope = (float(b['price']) - float(a['price'])) / hours
            rising.append({
                'direction': 'RISING',
                'candidate_key': f"MICROPOOL:RISING:{a['time']}:{b['time']}",
                'provenance': provenance(a, b),
                'anchor1': a,
                'anchor2': b,
                'elapsed_hours': hours,
                'slope_per_hour': slope,
                'absolute_slope_per_hour': abs(slope),
            })

    latest_confirmed_high = confirmed_highs[-1]['time'] if confirmed_highs else None
    latest_confirmed_low = confirmed_lows[-1]['time'] if confirmed_lows else None
    for row in falling:
        row['starts_from_latest_confirmed_directional_origin'] = (
            latest_confirmed_high is not None and row['anchor1']['time'] == latest_confirmed_high
        )
    for row in rising:
        row['starts_from_latest_confirmed_directional_origin'] = (
            latest_confirmed_low is not None and row['anchor1']['time'] == latest_confirmed_low
        )

    counts_by_provenance = {}
    for row in falling + rising:
        counts_by_provenance[row['provenance']] = counts_by_provenance.get(row['provenance'], 0) + 1

    payload = {
        'schema': 'nvt-micro-dow-pool/0.2',
        'status': 'RESEARCH_ONLY',
        'timeframe': args.timeframe,
        'cutoff': cutoff.isoformat(),
        'source_csv': str(src),
        'full_frozen_bar_count': len(frozen_all),
        'lookback_bars': len(bars),
        'rules': {
            'production_38_detector_unchanged': True,
            'production_38_uses_full_frozen_history': True,
            'local_radius': radius,
            'micro_high_confirmation': 'LOW1 -> rebound HIGH -> LOWER LOW',
            'micro_low_confirmation': 'HIGH1 -> pullback LOW -> HIGHER HIGH',
            'closed_bars_only': True,
            'production_writeback': False,
        },
        'production_context': {
            'confirmed_turn_count_full_history': len(turns.pivots),
            'active_leg': turns.active_leg,
            'active_threshold': turns.active_threshold,
            'latest_confirmed_high_time_in_lookback': latest_confirmed_high,
            'latest_confirmed_low_time_in_lookback': latest_confirmed_low,
        },
        'counts': {
            'micro_high_count': len(micro_highs),
            'micro_low_count': len(micro_lows),
            'confirmed_high_count_in_lookback': len(confirmed_highs),
            'confirmed_low_count_in_lookback': len(confirmed_lows),
            'falling_pair_count': len(falling),
            'rising_pair_count': len(rising),
            'pair_counts_by_provenance': counts_by_provenance,
        },
        'micro_highs': micro_highs,
        'micro_lows': micro_lows,
        'falling_pairs': falling,
        'rising_pairs': rising,
        'production_writeback': False,
        'normal_run_modified': False,
        'mt4_object_writeback': False,
        'trade_authority': False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'status': 'PASS',
        'output': str(out),
        **payload['counts'],
        'production_modified': False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
