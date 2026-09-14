from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from live_draw.geometry import build_channel_candidates, select_large_mid
from live_draw.market_input import load_ohlc_csv
from live_draw.normal_run import (
    TFS,
    normal_input_name,
    safe_symbol_filename,
    structural_event_end_indices,
)
from live_draw.turn_detector import detect_turns

LEVELS = ('LARGE_DOW', 'MID_DOW')
ROLES = {'TL', 'CH', 'TL_ZONE_EDGE', 'CH_ZONE_EDGE'}


def _selected_by_level(symbol: str, timeframe: str, bars):
    turns = detect_turns(bars)
    candidates = build_channel_candidates(bars, turns.pivots)
    large, mid, classifier = select_large_mid(symbol, timeframe, candidates)
    out = {'LARGE_DOW': large, 'MID_DOW': mid}
    return out, {
        'confirmed_turns': len(turns.pivots),
        'candidate_count': len(candidates),
        'classifier': classifier,
    }


def _geom_from_selected(selected):
    if selected is None:
        return None
    c = selected.candidate
    return {
        'direction': c.direction,
        'anchor1_time': c.anchor1.time.isoformat(),
        'anchor1_price': float(c.anchor1.price),
        'anchor2_time': c.anchor2.time.isoformat(),
        'anchor2_price': float(c.anchor2.price),
        'ch_offset': float(c.ch_offset),
        'zone_width': float(c.zone_width),
    }


def _geom_from_state(item):
    if item is None:
        return None
    return {
        'direction': item['direction'],
        'anchor1_time': item['anchor1_time'],
        'anchor1_price': float(item['anchor1_price']),
        'anchor2_time': item['anchor2_time'],
        'anchor2_price': float(item['anchor2_price']),
        'ch_offset': float(item['ch_offset']),
        'zone_width': float(item['zone_width']),
    }


def _same_geom(a, b, tol: float = 1e-10) -> tuple[bool, list[str]]:
    if a is None or b is None:
        return a is None and b is None, ([] if a is None and b is None else ['presence'])
    diffs = []
    for k in ('direction', 'anchor1_time', 'anchor2_time'):
        if a[k] != b[k]:
            diffs.append(k)
    for k in ('anchor1_price', 'anchor2_price', 'ch_offset', 'zone_width'):
        if not math.isclose(float(a[k]), float(b[k]), rel_tol=0.0, abs_tol=tol):
            diffs.append(k)
    return len(diffs) == 0, diffs


def _validate_snapshot(snapshot: Path, symbol: str) -> dict:
    if not snapshot.exists():
        return {'status': 'FAIL', 'reason': 'SNAPSHOT_MISSING', 'path': str(snapshot)}
    rows = []
    with snapshot.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        rows.extend(reader)
    if not rows:
        return {'status': 'FAIL', 'reason': 'SNAPSHOT_EMPTY', 'path': str(snapshot)}

    errors = []
    seen = set()
    for row in rows:
        oid = row.get('object_id', '')
        if not oid or oid in seen:
            errors.append(f'bad_object_id:{oid}')
        seen.add(oid)
        if row.get('symbol') != symbol:
            errors.append(f'symbol:{row.get("symbol")}')
        if row.get('timeframe') not in TFS:
            errors.append(f'timeframe:{row.get("timeframe")}')
        if row.get('role') not in ROLES:
            errors.append(f'role:{row.get("role")}')
        if row.get('generation_role') not in {'CURRENT', 'PREVIOUS'}:
            errors.append(f'generation_role:{row.get("generation_role")}')
        try:
            float(row.get('p1', ''))
            float(row.get('p2', ''))
        except Exception:
            errors.append(f'price:{oid}')

    return {
        'status': 'PASS' if not errors else 'FAIL',
        'rows': len(rows),
        'unique_object_ids': len(seen),
        'errors': errors,
        'path': str(snapshot),
    }


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    ap = argparse.ArgumentParser(description='NR7-1 USDJPY# regression audit')
    ap.add_argument('--input-dir', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--symbol', default='USDJPY#')
    ap.add_argument('--baseline-symbol', default='USDJPY')
    ap.add_argument('--report', default='')
    args = ap.parse_args()

    symbol = args.symbol.strip()
    baseline_symbol = args.baseline_symbol.strip()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    safe = safe_symbol_filename(symbol)

    state_path = output_dir / f'NORMAL_{safe}_live_state.json'
    normal_audit_path = output_dir / f'NORMAL_{safe}_run_audit.json'

    report = {
        'test': 'NR7-1_USDJPY_REGRESSION',
        'symbol': symbol,
        'baseline_symbol': baseline_symbol,
        'baseline_semantics': 'LAST_CONFIRMED_STRUCTURAL_EVENT',
        'regression_source': 'PUBLISHED_NORMAL_RUN_STATE_AND_AUDIT',
        'timeframes': {},
        'checks': {
            'same_final_current_geometry_as_baseline': True,
            'previous_is_immediate_rebuilt_generation': True,
            'all_inputs_present': True,
            'normal_run_state_present': state_path.exists(),
            'normal_run_audit_pass': False,
            'snapshot_valid': False,
        },
    }

    rebuilt_state = None
    if state_path.exists():
        try:
            rebuilt_state = _load_json(state_path)
        except Exception as exc:
            report['state_read_error'] = f'{type(exc).__name__}: {exc}'
            report['checks']['normal_run_state_present'] = False
    else:
        report['state_read_error'] = f'MISSING: {state_path}'

    normal_audit = None
    if normal_audit_path.exists():
        try:
            normal_audit = _load_json(normal_audit_path)
            report['normal_run_audit'] = normal_audit
            report['checks']['normal_run_audit_pass'] = (
                normal_audit.get('status') == 'PASS'
                and normal_audit.get('snapshot_published') is True
            )
        except Exception as exc:
            report['normal_run_audit'] = {
                'status': 'READ_ERROR',
                'error': f'{type(exc).__name__}: {exc}',
            }
    else:
        report['normal_run_audit'] = {'status': 'MISSING', 'path': str(normal_audit_path)}

    for tf in TFS:
        src = input_dir / normal_input_name(symbol, tf)
        tf_result = {'input': str(src)}
        if not src.exists():
            tf_result['status'] = 'FAIL_INPUT_MISSING'
            report['checks']['all_inputs_present'] = False
            report['checks']['same_final_current_geometry_as_baseline'] = False
            report['checks']['previous_is_immediate_rebuilt_generation'] = False
            report['timeframes'][tf] = tf_result
            continue

        if rebuilt_state is None or normal_audit is None:
            tf_result['status'] = 'FAIL_NORMAL_RUN_OUTPUT_MISSING'
            report['checks']['same_final_current_geometry_as_baseline'] = False
            report['checks']['previous_is_immediate_rebuilt_generation'] = False
            report['timeframes'][tf] = tf_result
            continue

        bars = load_ohlc_csv(src)
        event_indices = structural_event_end_indices(bars)
        baseline_bars = bars[:event_indices[-1] + 1] if event_indices else bars
        baseline_selected, baseline_meta = _selected_by_level(baseline_symbol, tf, baseline_bars)
        baseline_meta['structural_event_count'] = len(event_indices)
        baseline_meta['last_structural_event_index'] = event_indices[-1] if event_indices else None

        rebuild_audit = (normal_audit.get('timeframes') or {}).get(tf)
        if not isinstance(rebuild_audit, dict) or rebuild_audit.get('status') != 'PASS':
            tf_result['status'] = 'FAIL_REBUILD_AUDIT_MISSING'
            report['checks']['same_final_current_geometry_as_baseline'] = False
            report['checks']['previous_is_immediate_rebuilt_generation'] = False
            report['timeframes'][tf] = tf_result
            continue

        level_results = {}
        for level in LEVELS:
            expected = _geom_from_selected(baseline_selected[level])
            key = f'{symbol}|{tf}|{level}'
            slot = rebuilt_state.get('slots', {}).get(key)
            current = slot.get('current') if slot else None
            previous = slot.get('previous') if slot else None
            actual = _geom_from_state(current)
            same, diffs = _same_geom(expected, actual)
            if not same:
                report['checks']['same_final_current_geometry_as_baseline'] = False

            transitions = [x for x in rebuild_audit.get('transitions', []) if x.get('level') == level]
            adjacency_ok = True
            if current is None:
                adjacency_ok = baseline_selected[level] is None
            elif previous is None:
                adjacency_ok = len(transitions) <= 1
            else:
                adjacency_ok = (
                    int(previous['generation']) + 1 == int(current['generation'])
                    and len(transitions) >= 2
                    and transitions[-1]['generation'] == current['generation']
                    and transitions[-2]['generation'] == previous['generation']
                    and transitions[-1]['line_id'] == current['line_id']
                    and transitions[-2]['line_id'] == previous['line_id']
                )
            if not adjacency_ok:
                report['checks']['previous_is_immediate_rebuilt_generation'] = False

            level_results[level] = {
                'baseline_current': expected,
                'normal_current': actual,
                'same_current_geometry': same,
                'geometry_differences': diffs,
                'current_generation': current.get('generation') if current else None,
                'previous_generation': previous.get('generation') if previous else None,
                'transition_count': len(transitions),
                'previous_adjacency_ok': adjacency_ok,
            }

        tf_result.update({
            'status': 'PASS' if all(
                v['same_current_geometry'] and v['previous_adjacency_ok']
                for v in level_results.values()
            ) else 'FAIL',
            'bars': len(bars),
            'baseline_meta': baseline_meta,
            'rebuild': {
                'replay_strategy': rebuild_audit.get('replay_strategy'),
                'structural_event_count': rebuild_audit.get('structural_event_count'),
                'evaluated_prefixes': rebuild_audit.get('evaluated_prefixes'),
                'transition_count': rebuild_audit.get('transition_count'),
                'full_history_detector': rebuild_audit.get('full_history_detector'),
                'last_event_detector': rebuild_audit.get('last_event_detector'),
            },
            'levels': level_results,
        })
        report['timeframes'][tf] = tf_result

    snapshot = output_dir / f'NORMAL_{safe}_live_snapshot.csv'
    snap_result = _validate_snapshot(snapshot, symbol)
    report['snapshot'] = snap_result
    report['checks']['snapshot_valid'] = snap_result.get('status') == 'PASS'

    report['overall_status'] = 'PASS' if all(report['checks'].values()) else 'FAIL'

    report_path = Path(args.report) if args.report else output_dir / f'NR7_1_{safe}_regression.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['overall_status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
