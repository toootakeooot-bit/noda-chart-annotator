from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(str(value))


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Compare GT_0006 Gate-C candidates against one direct teacher trendline geometry sample.'
    )
    ap.add_argument('--gate-report', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--sample-time', default='2026-09-03T11:00:00')
    ap.add_argument('--sample-value', type=float, default=159.560)
    ap.add_argument('--tolerance', type=float, default=0.03)
    args = ap.parse_args()

    gate = load_json(args.gate_report)
    case = gate.get('cases', {}).get('GT_0006')
    if not case:
        raise ValueError('GT_0006 missing from gate report')

    rows = [r for r in case.get('candidates', []) if r.get('gate_C_A_and_B') is True]
    if not rows:
        raise ValueError('GT_0006 has no Gate-C survivors')

    sample_time = parse_dt(args.sample_time)
    scored = []
    for row in rows:
        t1 = parse_dt(row['anchor1_time'])
        elapsed_hours = (sample_time - t1).total_seconds() / 3600.0
        if elapsed_hours < 0:
            continue
        direction = row.get('direction')
        slope = float(row['absolute_slope_per_hour'])
        p1 = float(row['anchor1_price'])
        predicted = p1 - slope * elapsed_hours if direction == 'FALLING' else p1 + slope * elapsed_hours
        error = abs(predicted - args.sample_value)
        scored.append({
            'candidate_key': row.get('candidate_key'),
            'anchor1_time': row.get('anchor1_time'),
            'anchor1_price': row.get('anchor1_price'),
            'anchor2_time': row.get('anchor2_time'),
            'anchor2_price': row.get('anchor2_price'),
            'absolute_slope_per_hour': slope,
            'gentle_slope_rank_within_origin': row.get('gentle_slope_rank_within_origin'),
            'anchor2_recency_rank_within_origin': row.get('anchor2_recency_rank_within_origin'),
            'anchor2_low_wick_rank_within_origin': row.get('anchor2_low_wick_rank_within_origin'),
            'predicted_value_at_visual_sample': predicted,
            'absolute_error_vs_visual_sample': error,
            'within_visual_tolerance': error <= args.tolerance,
        })

    scored.sort(key=lambda r: (r['absolute_error_vs_visual_sample'], r['candidate_key'] or ''))
    finalists = [r for r in scored if r['within_visual_tolerance']]

    report = {
        'schema': 'nvt6-gt0006-visual-finalists/0.1',
        'status': 'RESEARCH_ONLY',
        'case_id': 'GT_0006',
        'visual_evidence': {
            'source_file': '分析共有_26-9-12.mp4',
            'teacher_interval': '00:30:50-00:31:49',
            'sample_video_time_approx': '00:31:12',
            'mt4_object_tooltip': 'Trendline 55257',
            'chart_status_bar_time': args.sample_time,
            'tooltip_line_value': args.sample_value,
            'match_tolerance': args.tolerance,
        },
        'input_gate_c_candidate_count': len(rows),
        'visual_finalist_count': len(finalists),
        'visual_finalists': finalists,
        'all_candidates_by_visual_error': scored,
        'interpretation': {
            'exact_teacher_anchor_locked': False,
            'reason': (
                'One direct line-value sample can reject most Gate-C candidates but does not '
                'reliably separate the remaining gentle family. Do not convert the lowest-error '
                'candidate into hard Ground Truth without an additional independent geometry sample '
                'or exact object parameters.'
            ),
            'selector_sequence': [
                'STRUCTURE_OWNERSHIP',
                'CLUSTER_RIGHT_EDGE_VALID_ALTERNATIVES',
                'OPTIONAL_LATER_HIGH_REANCHOR',
                'GENTLE_ANGLE_PREFERENCE',
                'WICK_NOISE_CONTEXT_TAG',
            ],
        },
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
        'gate_c_candidates': len(rows),
        'visual_finalists': len(finalists),
        'best_three': scored[:3],
        'exact_teacher_anchor_locked': False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
