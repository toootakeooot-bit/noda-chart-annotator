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


TARGET_CASES = ('GT_0006', 'GT_0007')


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def parse_dt(value: str) -> datetime:
    value = str(value).strip()
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return datetime.fromisoformat(value)


def resolve_pair(resolved: dict, case_id: str) -> dict:
    matches = []
    for pair in resolved.get('pairs', []):
        cases = {x.strip() for x in str(pair.get('cases', '')).split(',') if x.strip()}
        if case_id in cases:
            matches.append(pair)
    if len(matches) != 1:
        raise ValueError(f'{case_id}: expected one resolved pair, got {len(matches)}')
    return matches[0]


def infer_input_path(h1_csv: str, target_tf: str) -> Path:
    p = Path(h1_csv)
    name = p.name
    if not name.endswith('_H1.csv'):
        raise ValueError(f'cannot infer {target_tf} input from H1 filename: {name}')
    return p.with_name(name[:-7] + f'_{target_tf}.csv')


def closed_bars_proven_by_next_open(csv_path: Path, cutoff: datetime):
    bars = load_ohlc_csv(csv_path)
    if len(bars) < 2:
        return []
    out = []
    for i in range(len(bars) - 1):
        if bars[i + 1].time <= cutoff:
            out.append(bars[i])
        else:
            break
    return out


def higher_state(csv_path: Path, cutoff: datetime, direction: str) -> dict:
    bars = closed_bars_proven_by_next_open(csv_path, cutoff)
    if len(bars) < 3:
        return {
            'status': 'INSUFFICIENT',
            'closed_bar_count': len(bars),
            'active_leg': None,
            'direction_agrees': None,
            'latest_pivot': None,
            'latest_same_side_pivot': None,
            'latest_swing_amplitude': None,
        }
    turns = detect_turns(bars)
    pivots = turns.pivots
    same_kind = 'HIGH' if direction == 'FALLING' else 'LOW'
    same_side = [p for p in pivots if p.kind == same_kind]
    latest = pivots[-1] if pivots else None
    latest_same = same_side[-1] if same_side else None
    swing_amp = None
    if len(pivots) >= 2:
        swing_amp = abs(float(pivots[-1].price) - float(pivots[-2].price))
    return {
        'status': 'PASS',
        'closed_bar_count': len(bars),
        'active_leg': turns.active_leg,
        'direction_agrees': turns.active_leg == direction if turns.active_leg else None,
        'latest_pivot': (
            {'kind': latest.kind, 'time': latest.time.isoformat(), 'price': latest.price}
            if latest else None
        ),
        'latest_same_side_pivot': (
            {'kind': latest_same.kind, 'time': latest_same.time.isoformat(), 'price': latest_same.price}
            if latest_same else None
        ),
        'latest_swing_amplitude': swing_amp,
    }


def enrich_candidate(row: dict, peers: list[dict], higher_paths: dict[str, Path], cutoff: datetime) -> dict:
    a1 = row.get('anchor1', {})
    a2 = row.get('anchor2', {})
    direction = row['direction']
    t1 = parse_dt(a1['time'])

    same_origin = [
        r for r in peers
        if r['direction'] == direction
        and r.get('anchor1', {}).get('time') == a1.get('time')
        and r.get('provenance') == row.get('provenance')
    ]
    by_slope = sorted(same_origin, key=lambda r: float(r.get('absolute_slope_per_hour', 1e99)))
    by_recency = sorted(
        same_origin,
        key=lambda r: parse_dt(r.get('anchor2', {}).get('time')),
        reverse=True,
    )
    by_wick = sorted(
        same_origin,
        key=lambda r: float(r.get('anchor2', {}).get('wick_fraction_of_range', 1e99)),
    )

    def rank(rows: list[dict], key: str) -> int | None:
        for i, r in enumerate(rows, 1):
            if r.get('candidate_key') == key:
                return i
        return None

    higher = {}
    for tf, path in higher_paths.items():
        at_origin = higher_state(path, t1, direction)
        at_cutoff = higher_state(path, cutoff, direction)
        latest_same = at_origin.get('latest_same_side_pivot')
        distance = None
        normalized = None
        if latest_same:
            distance = abs(float(a1['price']) - float(latest_same['price']))
            amp = at_origin.get('latest_swing_amplitude')
            if amp and amp > 0:
                normalized = distance / amp
        higher[tf] = {
            'at_anchor1': at_origin,
            'at_cutoff': at_cutoff,
            'anchor1_price_distance_to_latest_same_side_pivot': distance,
            'anchor1_distance_over_latest_swing': normalized,
        }

    return {
        'candidate_key': row.get('candidate_key'),
        'direction': direction,
        'provenance': row.get('provenance'),
        'starts_from_latest_confirmed_directional_origin': row.get(
            'starts_from_latest_confirmed_directional_origin'
        ),
        'anchor1_time': a1.get('time'),
        'anchor1_price': a1.get('price'),
        'anchor1_wick_fraction_of_range': a1.get('wick_fraction_of_range'),
        'anchor2_time': a2.get('time'),
        'anchor2_price': a2.get('price'),
        'anchor2_wick_fraction_of_range': a2.get('wick_fraction_of_range'),
        'elapsed_hours': row.get('elapsed_hours'),
        'absolute_slope_per_hour': row.get('absolute_slope_per_hour'),
        'same_origin_peer_count': len(same_origin),
        'gentle_slope_rank_within_origin': rank(by_slope, row.get('candidate_key')),
        'anchor2_recency_rank_within_origin': rank(by_recency, row.get('candidate_key')),
        'anchor2_low_wick_rank_within_origin': rank(by_wick, row.get('candidate_key')),
        'higher_timeframe_context': higher,
    }


def summarize_case(case_id: str, pool: dict, pair: dict) -> dict:
    cutoff = parse_dt(pair['exact_cutoff'])
    all_rows = list(pool.get('falling_pairs', [])) + list(pool.get('rising_pairs', []))
    latest_bridge = [
        r for r in all_rows
        if r.get('provenance') == 'P38_MICRO'
        and r.get('starts_from_latest_confirmed_directional_origin')
    ]

    h4 = infer_input_path(pair['input_csv'], 'H4')
    d1 = infer_input_path(pair['input_csv'], 'D1')
    for p in (h4, d1):
        if not p.exists():
            raise FileNotFoundError(str(p))

    features = [
        enrich_candidate(r, all_rows, {'H4': h4, 'D1': d1}, cutoff)
        for r in latest_bridge
    ]

    direction_counts = {}
    for r in features:
        d = r['direction']
        direction_counts[d] = direction_counts.get(d, 0) + 1

    h4_agree_origin = sum(
        1 for r in features
        if r['higher_timeframe_context']['H4']['at_anchor1'].get('direction_agrees') is True
    )
    d1_agree_origin = sum(
        1 for r in features
        if r['higher_timeframe_context']['D1']['at_anchor1'].get('direction_agrees') is True
    )

    return {
        'case_id': case_id,
        'source_id': pair['source_id'],
        'timeframe': pair['timeframe'],
        'exact_cutoff': pair['exact_cutoff'],
        'latest_origin_p38_micro_count': len(features),
        'direction_counts': direction_counts,
        'h4_direction_agreement_at_origin_count': h4_agree_origin,
        'd1_direction_agreement_at_origin_count': d1_agree_origin,
        'features': features,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Probe candidate-level ownership features without selecting or drawing a line.'
    )
    ap.add_argument('--resolved-cutoffs', required=True)
    ap.add_argument('--ownership-dir', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    resolved = load_json(Path(args.resolved_cutoffs))
    ownership_dir = Path(args.ownership_dir)

    cases = {}
    for cid in TARGET_CASES:
        pair = resolve_pair(resolved, cid)
        if pair.get('timeframe') != 'H1':
            raise ValueError(f'{cid}: expected H1 pair')
        pool_path = ownership_dir / f"{pair['source_id']}_H1_MICRO_DOW_POOL.json"
        if not pool_path.exists():
            raise FileNotFoundError(str(pool_path))
        pool = load_json(pool_path)
        cases[cid] = summarize_case(cid, pool, pair)

    gt6 = cases['GT_0006']
    gt7 = cases['GT_0007']

    report = {
        'schema': 'nvt6-ownership-feature-probe/0.2',
        'status': 'RESEARCH_ONLY',
        'cases': cases,
        'comparison_guards': {
            'gt0006_is_positive_h1_line_case': True,
            'gt0007_is_timeframe_global_no_line_control': True,
            'gt0005_processed_before_gt0006_as_display_suppression_control': True,
            'gt0005_excluded_from_ownership_negative_learning': True,
            'gt0005_reason': (
                'GT_0005 is a valid small-Dow turn line that is intentionally not displayed because '
                'its steep angle makes it short-lived and showing every such line would create '
                'display clutter. It is not an ownership rejection.'
            ),
            'single_positive_single_negative_control_cannot_fix_production_rule': True,
        },
        'coarse_observations': {
            'gt0006_latest_origin_bridge_count': gt6['latest_origin_p38_micro_count'],
            'gt0007_latest_origin_bridge_count': gt7['latest_origin_p38_micro_count'],
            'gt0006_h4_direction_agreement_at_origin_count': gt6[
                'h4_direction_agreement_at_origin_count'
            ],
            'gt0007_h4_direction_agreement_at_origin_count': gt7[
                'h4_direction_agreement_at_origin_count'
            ],
            'gt0006_d1_direction_agreement_at_origin_count': gt6[
                'd1_direction_agreement_at_origin_count'
            ],
            'gt0007_d1_direction_agreement_at_origin_count': gt7[
                'd1_direction_agreement_at_origin_count'
            ],
        },
        'next_hypotheses': [
            'higher_timeframe_direction/context may gate H1 ownership',
            'candidate origin recency/role may matter beyond P38 provenance',
            'peer-relative slope rank may matter only after ownership is established',
            'anchor2 wick strength should be treated as a penalty/tag, not a hard deletion',
            'cluster-right-edge still requires a separate evidence-driven cluster definition',
            'GT_0005 steep-angle age/lifetime and display-clutter policy belong to later visibility/lifecycle scoring',
        ],
        'interpretation_guard': (
            'This probe extracts ownership features only. It does not define an ownership rule, '
            'does not select a teacher line, and must not modify production NCA or MT4. GT_0005 '
            'display suppression is intentionally kept separate from ownership validity.'
        ),
        'production_writeback': False,
        'normal_run_modified': False,
        'mt4_object_writeback': False,
        'trade_authority': False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'status': 'PASS',
        'output': str(out),
        **report['coarse_observations'],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
