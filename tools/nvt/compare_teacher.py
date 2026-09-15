from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

UNKNOWN_VALUES = {None, '', 'UNKNOWN', 'PENDING', 'N/A'}


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def is_known(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().upper() not in {str(v).upper() for v in UNKNOWN_VALUES if isinstance(v, str)}
    return value not in UNKNOWN_VALUES


def norm_direction(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().upper()
    if value in {'UP', 'RISING', 'BULL', 'BULLISH'}:
        return 'RISING'
    if value in {'DOWN', 'FALLING', 'BEAR', 'BEARISH'}:
        return 'FALLING'
    return value


def symbol_equivalent(teacher_symbol: str | None, broker_symbol: str | None) -> bool:
    """Research-only equivalence for reference notation vs XM broker symbol.

    Production NCA keeps the exact XM MT4 Symbol() string canonical. NVT source
    evidence may label USDJPY while the XM dump is USDJPY#. Only that single
    trailing-# difference is accepted here; broader alias guessing is prohibited.
    """
    if not teacher_symbol or not broker_symbol:
        return False
    a = teacher_symbol.strip()
    b = broker_symbol.strip()
    if a == b:
        return True
    return (a + '#') == b or (b + '#') == a


def candidate_selected(candidate: dict, dump: dict) -> bool:
    cid = candidate.get('candidate_id')
    return bool(
        candidate.get('selected_as_large')
        or candidate.get('selected_as_mid')
        or cid == dump.get('selected_large_candidate_id')
        or cid == dump.get('selected_mid_candidate_id')
    )


def anchor_match_distance(teacher_time: str, candidate_anchor: dict, candidates: list[dict]) -> int | None:
    """Return candidate-bar distance from exact teacher timestamp when resolvable.

    Candidate dumps expose bar_index for every pivot but not a full bar-index map.
    We therefore resolve the teacher timestamp against all pivot timestamps visible
    in the dump. If the exact timestamp is absent from the pivot universe, the
    distance is unknown rather than guessed.
    """
    time_to_indices: dict[str, set[int]] = {}
    for c in candidates:
        for name in ('anchor1', 'anchor2', 'ch_anchor'):
            p = c.get(name) or {}
            t = p.get('time')
            idx = p.get('bar_index')
            if t is not None and idx is not None:
                time_to_indices.setdefault(str(t), set()).add(int(idx))
    indices = time_to_indices.get(str(teacher_time))
    if not indices:
        return None
    cand_idx = candidate_anchor.get('bar_index')
    if cand_idx is None:
        return None
    return min(abs(int(cand_idx) - idx) for idx in indices)


def compare_teacher_object(obj: dict, dump: dict, tolerance_bars: int) -> dict:
    candidates = dump.get('candidates') or []
    direction = norm_direction(obj.get('direction'))
    a1_time = obj.get('anchor1_time')
    a2_time = obj.get('anchor2_time')

    result = {
        'teacher_object_id': obj.get('object_id'),
        'object_type': obj.get('object_type'),
        'teacher_role': obj.get('teacher_role'),
        'teacher_direction': direction,
        'anchor_data_complete': bool(is_known(a1_time) and is_known(a2_time)),
        'candidate_present': None,
        'matched_candidate_id': None,
        'anchor_match': 'PENDING_GT_ANCHORS',
        'selector_match': None,
        'channel_match': 'NOT_ASSESSED',
        'failure_classes': [],
        'candidate_matches': [],
    }

    if obj.get('object_type') not in {'TL', 'CHANNEL', 'CH'}:
        result['failure_classes'].append('ROLE_OR_OBJECT_TYPE_NOT_SUPPORTED_YET')
        return result

    if not result['anchor_data_complete']:
        result['failure_classes'].append('GROUND_TRUTH_ANCHORS_PENDING')
        return result

    matches = []
    for c in candidates:
        if direction and c.get('direction') != direction:
            continue
        d1 = anchor_match_distance(str(a1_time), c.get('anchor1') or {}, candidates)
        d2 = anchor_match_distance(str(a2_time), c.get('anchor2') or {}, candidates)
        if d1 is None or d2 is None:
            continue
        if d1 <= tolerance_bars and d2 <= tolerance_bars:
            matches.append({
                'candidate_id': c.get('candidate_id'),
                'anchor1_bar_distance': d1,
                'anchor2_bar_distance': d2,
                'selected': candidate_selected(c, dump),
                'direction': c.get('direction'),
                'ch_anchor': c.get('ch_anchor'),
            })

    result['candidate_matches'] = matches
    result['candidate_present'] = bool(matches)

    if not matches:
        result['anchor_match'] = 'OUTSIDE_TOLERANCE_OR_ABSENT'
        result['selector_match'] = False
        result['failure_classes'].append('CANDIDATE_ABSENT')
        return result

    best = min(matches, key=lambda m: (m['anchor1_bar_distance'] + m['anchor2_bar_distance'], not m['selected']))
    result['matched_candidate_id'] = best['candidate_id']
    max_dist = max(best['anchor1_bar_distance'], best['anchor2_bar_distance'])
    result['anchor_match'] = 'EXACT_BAR' if max_dist == 0 else f'WITHIN_{tolerance_bars}_BAR'
    result['selector_match'] = any(m['selected'] for m in matches)
    if not result['selector_match']:
        result['failure_classes'].append('SELECTION')

    teacher_ch_time = obj.get('ch_anchor_time') or obj.get('opposite_anchor_time')
    if is_known(teacher_ch_time):
        result['channel_match'] = 'PENDING_CH_TIME_RESOLUTION'
    else:
        result['channel_match'] = 'PENDING_GT_CHANNEL_ANCHOR'

    return result


def compare_case(gt: dict, dump: dict, tolerance_bars: int) -> dict:
    case_id = gt.get('case_id')
    symbol_match = symbol_equivalent(gt.get('symbol'), dump.get('symbol'))
    timeframe_match = gt.get('timeframe') == dump.get('timeframe')
    teacher_objects = gt.get('teacher_objects') or []

    report = {
        'schema': 'nvt-teacher-nca-diff/1.0',
        'case_id': case_id,
        'ground_truth_status': gt.get('annotation_status'),
        'teacher_symbol': gt.get('symbol'),
        'candidate_dump_symbol': dump.get('symbol'),
        'timeframe': gt.get('timeframe'),
        'candidate_dump_cutoff': dump.get('effective_last_closed_bar'),
        'symbol_match': symbol_match,
        'symbol_match_policy': 'EXACT_OR_SINGLE_TRAILING_HASH_ONLY',
        'timeframe_match': timeframe_match,
        'structure_scale_match': timeframe_match,
        'anchor_tolerance_bars': tolerance_bars,
        'expected_no_line': len(teacher_objects) == 0,
        'no_line_match': None,
        'teacher_object_results': [],
        'failure_classes': [],
        'assessment_status': 'PENDING',
    }

    if not symbol_match:
        report['failure_classes'].append('SYMBOL_MISMATCH')
    if not timeframe_match:
        report['failure_classes'].append('STRUCTURE_SCALE_MISMATCH')

    if report['expected_no_line']:
        selected_ids = [x for x in (dump.get('selected_large_candidate_id'), dump.get('selected_mid_candidate_id')) if x]
        report['no_line_match'] = len(selected_ids) == 0
        if not report['no_line_match']:
            report['failure_classes'].append('NO_LINE_MISMATCH')
        report['assessment_status'] = 'PASS' if not report['failure_classes'] else 'FAIL'
        return report

    for obj in teacher_objects:
        obj_result = compare_teacher_object(obj, dump, tolerance_bars)
        report['teacher_object_results'].append(obj_result)
        report['failure_classes'].extend(obj_result.get('failure_classes') or [])

    report['failure_classes'] = list(dict.fromkeys(report['failure_classes']))
    pending_only = {'GROUND_TRUTH_ANCHORS_PENDING', 'PENDING_GT_CHANNEL_ANCHOR'}
    hard_failures = [f for f in report['failure_classes'] if f not in pending_only]
    complete_objects = all(r.get('anchor_data_complete') for r in report['teacher_object_results'])

    if hard_failures:
        report['assessment_status'] = 'FAIL'
    elif complete_objects:
        report['assessment_status'] = 'PASS'
    else:
        report['assessment_status'] = 'PENDING_GROUND_TRUTH'
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description='NVT3 - compare Teacher Ground Truth against an NVT2 candidate dump')
    ap.add_argument('--ground-truth', required=True)
    ap.add_argument('--candidate-dump', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--anchor-tolerance-bars', type=int, default=1)
    args = ap.parse_args()

    if args.anchor_tolerance_bars < 0:
        raise ValueError('anchor tolerance must be >= 0')

    gt = load_json(args.ground_truth)
    dump = load_json(args.candidate_dump)
    if gt.get('schema') != 'nvt-ground-truth/1.0':
        raise ValueError(f'unexpected Ground Truth schema: {gt.get("schema")}')
    if dump.get('schema') != 'nvt-candidate-dump/1.0':
        raise ValueError(f'unexpected candidate dump schema: {dump.get("schema")}')

    report = compare_case(gt, dump, args.anchor_tolerance_bars)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'status': report['assessment_status'],
        'case_id': report['case_id'],
        'failure_classes': report['failure_classes'],
        'output': str(out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
