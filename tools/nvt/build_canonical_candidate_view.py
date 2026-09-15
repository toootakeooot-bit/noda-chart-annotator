from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def resolve_candidate_dump(args) -> Path:
    if args.candidate_dump:
        return Path(args.candidate_dump)
    summary = load_json(Path(args.replay_summary))
    rows = summary if isinstance(summary, list) else summary.get('pairs') or summary.get('cases') or []
    matches = [
        r for r in rows
        if str(r.get('source_id')) == args.source_id and str(r.get('timeframe')) == args.timeframe
    ]
    if len(matches) != 1:
        raise ValueError(f'expected one replay summary match, got {len(matches)}')
    return Path(matches[0]['candidate_dump'])


def geometry_key(row: dict) -> str:
    ch = row.get('ch_anchor', {}) or {}
    return '|'.join([
        str(row.get('candidate_id')),
        'CH',
        str(ch.get('time')),
        str(ch.get('price')),
        str(row.get('ch_offset')),
        str(row.get('zone_width')),
    ])


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Build a research-only canonical geometry view without collapsing context metrics.'
    )
    ap.add_argument('--candidate-dump')
    ap.add_argument('--replay-summary')
    ap.add_argument('--source-id', default='NVT_VIDEO_20260830')
    ap.add_argument('--timeframe', default='H4')
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    if not args.candidate_dump and not args.replay_summary:
        raise ValueError('provide --candidate-dump or --replay-summary')

    candidate_path = resolve_candidate_dump(args)
    payload = load_json(candidate_path)
    candidates = payload.get('candidates', [])

    groups = defaultdict(list)
    for row in candidates:
        groups[geometry_key(row)].append(row)

    canonical = []
    unsafe_groups = []
    for key, rows in sorted(groups.items()):
        base = rows[0]
        stable_fields = [
            'candidate_id', 'direction', 'tl_contacts', 'ch_contacts', 'unbroken_close',
            'ch_offset', 'zone_width', 'slope_per_second',
        ]
        unstable = []
        for field in stable_fields:
            vals = {json.dumps(r.get(field), sort_keys=True) for r in rows}
            if len(vals) > 1:
                unstable.append(field)

        anchor1_vals = {json.dumps(r.get('anchor1', {}), sort_keys=True) for r in rows}
        anchor2_vals = {json.dumps(r.get('anchor2', {}), sort_keys=True) for r in rows}
        ch_vals = {json.dumps(r.get('ch_anchor', {}), sort_keys=True) for r in rows}
        if len(anchor1_vals) > 1:
            unstable.append('anchor1')
        if len(anchor2_vals) > 1:
            unstable.append('anchor2')
        if len(ch_vals) > 1:
            unstable.append('ch_anchor')

        turn_spans = sorted({r.get('turn_span') for r in rows if r.get('turn_span') is not None})
        selected_large = any(bool(r.get('selected_as_large')) for r in rows)
        selected_mid = any(bool(r.get('selected_as_mid')) for r in rows)

        item = {
            'geometry_key': key,
            'candidate_id': base.get('candidate_id'),
            'direction': base.get('direction'),
            'anchor1': base.get('anchor1'),
            'anchor2': base.get('anchor2'),
            'ch_anchor': base.get('ch_anchor'),
            'slope_per_second': base.get('slope_per_second'),
            'tl_contacts': base.get('tl_contacts'),
            'ch_contacts': base.get('ch_contacts'),
            'unbroken_close': base.get('unbroken_close'),
            'ch_offset': base.get('ch_offset'),
            'zone_width': base.get('zone_width'),
            'source_row_count': len(rows),
            'context_variant_count': len(turn_spans),
            'turn_span_values': turn_spans,
            'turn_span_min': min(turn_spans) if turn_spans else None,
            'turn_span_max': max(turn_spans) if turn_spans else None,
            'selected_as_large': selected_large,
            'selected_as_mid': selected_mid,
            'canonical_status': (
                'SAFE_GEOMETRY_WITH_CONTEXT_VARIANTS'
                if not unstable else 'UNSAFE_GEOMETRY_VARIATION'
            ),
            'unstable_fields': sorted(set(unstable)),
        }
        canonical.append(item)
        if unstable:
            unsafe_groups.append(item)

    report = {
        'schema': 'nvt-canonical-candidate-view/0.1',
        'status': 'RESEARCH_ONLY',
        'source_candidate_dump': str(candidate_path),
        'source_id': args.source_id,
        'timeframe': args.timeframe,
        'source_row_count': len(candidates),
        'canonical_geometry_count': len(canonical),
        'collapsed_row_excess_count': len(candidates) - len(canonical),
        'unsafe_geometry_group_count': len(unsafe_groups),
        'selected_geometry_collision_count': sum(
            1 for x in unsafe_groups if x['selected_as_large'] or x['selected_as_mid']
        ),
        'identity_policy': {
            'geometry_identity': (
                'candidate_id + CH anchor time/price + ch_offset + zone_width'
            ),
            'context_metrics_not_collapsed': ['turn_span'],
            'scoring_guard': (
                'Do not score duplicate source rows independently. Use one geometry record and '
                'treat turn_span as a context range until upstream duplication semantics are fixed.'
            ),
        },
        'canonical_candidates': canonical,
        'unsafe_groups': unsafe_groups,
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
        'source_row_count': len(candidates),
        'canonical_geometry_count': len(canonical),
        'collapsed_row_excess_count': len(candidates) - len(canonical),
        'unsafe_geometry_group_count': len(unsafe_groups),
        'selected_geometry_collision_count': report['selected_geometry_collision_count'],
        'output': str(out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
