from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def expected_no_line(gt: dict) -> bool:
    notes = [str(x) for x in gt.get('notes', [])]
    return len(gt.get('teacher_objects', [])) == 0 and any(
        x.startswith('expected_no_line=') for x in notes
    )


def infer_no_line_scope(gt: dict) -> tuple[str, str | None]:
    tf = str(gt.get('timeframe') or '')
    for raw in gt.get('notes', []):
        note = str(raw)
        if not note.startswith('expected_no_line='):
            continue
        value = note.split('=', 1)[1].strip()
        if value == tf:
            return 'TIMEFRAME_GLOBAL', note
        return 'STRUCTURE_SPECIFIC', note
    return 'UNKNOWN', None


def main() -> int:
    ap = argparse.ArgumentParser(description='Evaluate NVT structure-ownership evidence for one case.')
    ap.add_argument('--ground-truth', required=True)
    ap.add_argument('--micro-pool', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    gt = load_json(args.ground_truth)
    pool = load_json(args.micro_pool)
    case_id = gt['case_id']
    tf = gt['timeframe']

    if pool.get('timeframe') != tf:
        raise ValueError(f"timeframe mismatch: GT={tf} pool={pool.get('timeframe')}")

    no_line = expected_no_line(gt)
    no_line_scope, no_line_scope_note = infer_no_line_scope(gt)
    teacher_objects = gt.get('teacher_objects', [])
    teacher_line_expected = bool(teacher_objects)
    teacher_direction = None
    if teacher_objects:
        teacher_direction = teacher_objects[0].get('direction')

    if teacher_direction == 'DOWN':
        rows = list(pool.get('falling_pairs', []))
    elif teacher_direction == 'UP':
        rows = list(pool.get('rising_pairs', []))
    else:
        rows = list(pool.get('falling_pairs', [])) + list(pool.get('rising_pairs', []))

    counts = {}
    for row in rows:
        p = row.get('provenance', 'UNKNOWN')
        counts[p] = counts.get(p, 0) + 1

    latest_origin_bridge = [
        r for r in rows
        if r.get('provenance') in {'P38_MICRO', 'MICRO_P38'}
        and r.get('starts_from_latest_confirmed_directional_origin')
    ]
    latest_origin_bridge.sort(
        key=lambda r: (r.get('absolute_slope_per_hour', 1e99), -r.get('elapsed_hours', 0.0))
    )

    p38_micro = [r for r in rows if r.get('provenance') == 'P38_MICRO']
    p38_p38 = [r for r in rows if r.get('provenance') == 'P38_P38']
    micro_micro = [r for r in rows if r.get('provenance') == 'MICRO_MICRO']

    if no_line and no_line_scope == 'TIMEFRAME_GLOBAL':
        observation = (
            'TIMEFRAME_GLOBAL_NEGATIVE_CONTROL_HAS_CANDIDATES'
            if rows else 'TIMEFRAME_GLOBAL_NO_LINE_BY_ABSENCE_ONLY'
        )
    elif no_line and no_line_scope == 'STRUCTURE_SPECIFIC':
        observation = 'STRUCTURE_SPECIFIC_NO_LINE_TARGET_NOT_IDENTIFIED'
    elif no_line:
        observation = 'NO_LINE_SCOPE_UNRESOLVED'
    elif teacher_line_expected:
        if latest_origin_bridge:
            observation = 'POSITIVE_RECALL_FROM_LATEST_P38_ORIGIN'
        elif p38_micro:
            observation = 'POSITIVE_RECALL_P38_MICRO_PRESENT'
        elif p38_p38:
            observation = 'NATIVE_P38_P38_PRESENT'
        else:
            observation = 'OWNERSHIP_RECALL_UNRESOLVED'
    else:
        observation = 'GROUND_TRUTH_EXPECTATION_UNRESOLVED'

    def slim(row: dict) -> dict:
        a1 = row.get('anchor1', {})
        a2 = row.get('anchor2', {})
        return {
            'candidate_key': row.get('candidate_key'),
            'direction': row.get('direction'),
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
        }

    out = {
        'schema': 'nvt-structure-ownership-evidence/0.2',
        'status': 'RESEARCH_ONLY',
        'case_id': case_id,
        'source_id': gt.get('source_id'),
        'timeframe': tf,
        'teacher_expectation': {
            'expected_no_line': no_line,
            'no_line_scope': no_line_scope,
            'no_line_scope_source_note': no_line_scope_note,
            'no_line_scope_status': 'PROVISIONAL_UNTIL_SCHEMA_AMENDMENT_FIXED',
            'teacher_line_expected': teacher_line_expected,
            'teacher_direction': teacher_direction,
            'teacher_object_count': len(teacher_objects),
        },
        'candidate_evidence': {
            'directional_candidate_count': len(rows),
            'provenance_counts': counts,
            'p38_p38_count': len(p38_p38),
            'p38_micro_count': len(p38_micro),
            'micro_micro_count': len(micro_micro),
            'latest_origin_bridge_count': len(latest_origin_bridge),
            'latest_origin_bridge_gentlest_top10': [slim(r) for r in latest_origin_bridge[:10]],
        },
        'observation': observation,
        'interpretation_guard': (
            'This report does not select a line and does not define a production ownership rule. '
            'A STRUCTURE_SPECIFIC NO-LINE case cannot label every other candidate on the same '
            'timeframe/cutoff as negative. The rejected structure must be identified separately.'
        ),
        'hypothesis_under_test': {
            'P38_P38': 'native same-timeframe candidate hypothesis',
            'P38_MICRO': 'same-timeframe bridge candidate hypothesis',
            'MICRO_MICRO': 'nested/internal candidate hypothesis',
            'MICRO_P38': 'unresolved transition hypothesis',
        },
        'production_writeback': False,
        'normal_run_modified': False,
        'mt4_object_writeback': False,
        'trade_authority': False,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'status': 'PASS',
        'case_id': case_id,
        'observation': observation,
        'no_line_scope': no_line_scope,
        'provenance_counts': counts,
        'latest_origin_bridge_count': len(latest_origin_bridge),
        'output': str(out_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
