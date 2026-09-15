from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def scalar_signature(row: dict) -> tuple:
    return (
        row.get('turn_span'),
        row.get('tl_contacts'),
        row.get('ch_contacts'),
        row.get('unbroken_close'),
        row.get('ch_offset'),
        row.get('zone_width'),
        row.get('slope_per_second'),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description='Audit NVT candidate identity collisions/duplicates.')
    ap.add_argument('--candidate-dump')
    ap.add_argument('--replay-summary')
    ap.add_argument('--source-id', default='NVT_VIDEO_20260830')
    ap.add_argument('--timeframe', default='H4')
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    candidate_path = None
    if args.candidate_dump:
        candidate_path = Path(args.candidate_dump)
    elif args.replay_summary:
        summary = load_json(Path(args.replay_summary))
        rows = summary if isinstance(summary, list) else summary.get('pairs') or summary.get('cases') or []
        matches = [
            r for r in rows
            if str(r.get('source_id')) == args.source_id and str(r.get('timeframe')) == args.timeframe
        ]
        if len(matches) != 1:
            raise ValueError(f'expected one replay summary match, got {len(matches)}')
        candidate_path = Path(matches[0]['candidate_dump'])
    else:
        raise ValueError('provide --candidate-dump or --replay-summary')

    payload = load_json(candidate_path)
    candidates = payload.get('candidates', [])
    by_id = defaultdict(list)
    for row in candidates:
        by_id[str(row.get('candidate_id'))].append(row)

    duplicate_groups = []
    for cid, rows in sorted(by_id.items()):
        if len(rows) <= 1:
            continue
        ch_keys = {
            (
                r.get('ch_anchor', {}).get('time'),
                r.get('ch_anchor', {}).get('price'),
            )
            for r in rows
        }
        signatures = {scalar_signature(r) for r in rows}
        selected_large = any(bool(r.get('selected_as_large')) for r in rows)
        selected_mid = any(bool(r.get('selected_as_mid')) for r in rows)

        if len(ch_keys) > 1:
            cls = 'SAME_TL_DIFFERENT_CH'
        elif len(signatures) > 1:
            cls = 'SAME_GEOMETRY_DIFFERENT_CONTEXT_METRICS'
        else:
            cls = 'EXACT_DUPLICATE_ROWS'

        duplicate_groups.append({
            'candidate_id': cid,
            'row_count': len(rows),
            'classification': cls,
            'unique_ch_anchor_count': len(ch_keys),
            'unique_metric_signature_count': len(signatures),
            'selected_as_large': selected_large,
            'selected_as_mid': selected_mid,
            'variants': [
                {
                    'ch_anchor_time': r.get('ch_anchor', {}).get('time'),
                    'ch_anchor_price': r.get('ch_anchor', {}).get('price'),
                    'turn_span': r.get('turn_span'),
                    'tl_contacts': r.get('tl_contacts'),
                    'ch_contacts': r.get('ch_contacts'),
                    'unbroken_close': r.get('unbroken_close'),
                    'ch_offset': r.get('ch_offset'),
                    'zone_width': r.get('zone_width'),
                }
                for r in rows
            ],
        })

    class_counts = {}
    for g in duplicate_groups:
        c = g['classification']
        class_counts[c] = class_counts.get(c, 0) + 1

    selected_collision_groups = [
        g for g in duplicate_groups if g['selected_as_large'] or g['selected_as_mid']
    ]

    report = {
        'schema': 'nvt-candidate-identity-audit/0.1',
        'status': 'RESEARCH_ONLY',
        'source_candidate_dump': str(candidate_path),
        'source_id': args.source_id,
        'timeframe': args.timeframe,
        'candidate_row_count': len(candidates),
        'unique_candidate_id_count': len(by_id),
        'duplicate_candidate_id_group_count': len(duplicate_groups),
        'duplicate_row_excess_count': sum(g['row_count'] - 1 for g in duplicate_groups),
        'classification_counts': class_counts,
        'selected_candidate_collision_group_count': len(selected_collision_groups),
        'selected_candidate_collision_groups': selected_collision_groups,
        'duplicate_groups': duplicate_groups,
        'interpretation': {
            'id_definition_observed': 'direction + TL anchor1 time + TL anchor2 time',
            'risk': (
                'Rows with the same candidate_id may carry different CH anchors or structural metrics. '
                'Selector metrics must not treat such rows as one unambiguous candidate without an explicit identity policy.'
            ),
            'next_decision': (
                'If SAME_TL_DIFFERENT_CH dominates, split TL identity from channel-variant identity. '
                'If SAME_GEOMETRY_DIFFERENT_CONTEXT_METRICS remains, audit upstream pivot/context duplication before NVT6 scoring.'
            ),
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
        'candidate_row_count': len(candidates),
        'unique_candidate_id_count': len(by_id),
        'duplicate_candidate_id_group_count': len(duplicate_groups),
        'classification_counts': class_counts,
        'selected_candidate_collision_group_count': len(selected_collision_groups),
        'output': str(out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
