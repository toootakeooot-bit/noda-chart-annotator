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


def anchor_geometry(anchor: dict | None) -> tuple:
    a = anchor or {}
    return (a.get('kind'), a.get('time'), a.get('price'))


def anchor_metadata(anchor: dict | None) -> dict:
    a = dict(anchor or {})
    for k in ('kind', 'time', 'price'):
        a.pop(k, None)
    return a


def geometry_key(row: dict) -> str:
    a1 = row.get('anchor1', {}) or {}
    a2 = row.get('anchor2', {}) or {}
    ch = row.get('ch_anchor', {}) or {}
    return '|'.join([
        str(row.get('direction')),
        'TL1', str(a1.get('time')), str(a1.get('price')),
        'TL2', str(a2.get('time')), str(a2.get('price')),
        'CH', str(ch.get('time')), str(ch.get('price')),
        'OFF', str(row.get('ch_offset')),
        'ZONE', str(row.get('zone_width')),
        'SLOPE', str(row.get('slope_per_second')),
    ])


def distinct_values(rows: list[dict], field: str) -> list:
    vals = []
    seen = set()
    for r in rows:
        v = r.get(field)
        key = json.dumps(v, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            vals.append(v)
    return vals


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Build research-only canonical geometry view while separating geometry from context metadata.'
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
    candidate_id_to_geometry_keys = defaultdict(set)
    for row in candidates:
        key = geometry_key(row)
        groups[key].append(row)
        candidate_id_to_geometry_keys[str(row.get('candidate_id'))].add(key)

    canonical = []
    unsafe_geometry_groups = []
    context_variant_groups = []
    metadata_variant_groups = []

    for key, rows in sorted(groups.items()):
        base = rows[0]

        # Geometry-critical fields. Context metrics such as turn_span/contact counts
        # intentionally do NOT make a geometry unsafe.
        geometry_unstable = []
        for field in ('direction', 'ch_offset', 'zone_width', 'slope_per_second'):
            if len(distinct_values(rows, field)) > 1:
                geometry_unstable.append(field)

        for name in ('anchor1', 'anchor2', 'ch_anchor'):
            vals = {json.dumps(anchor_geometry(r.get(name)), ensure_ascii=False) for r in rows}
            if len(vals) > 1:
                geometry_unstable.append(name + '_geometry')

        context_fields = ('turn_span', 'tl_contacts', 'ch_contacts', 'unbroken_close')
        context_values = {f: distinct_values(rows, f) for f in context_fields}
        context_variant_fields = [f for f, vals in context_values.items() if len(vals) > 1]

        metadata_variant_fields = []
        for name in ('anchor1', 'anchor2', 'ch_anchor'):
            vals = {
                json.dumps(anchor_metadata(r.get(name)), sort_keys=True, ensure_ascii=False)
                for r in rows
            }
            if len(vals) > 1:
                metadata_variant_fields.append(name)

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
            'ch_offset': base.get('ch_offset'),
            'zone_width': base.get('zone_width'),
            'source_row_count': len(rows),
            'selected_as_large': selected_large,
            'selected_as_mid': selected_mid,
            'geometry_status': 'SAFE_GEOMETRY' if not geometry_unstable else 'UNSAFE_GEOMETRY',
            'geometry_unstable_fields': sorted(set(geometry_unstable)),
            'context_variant_fields': sorted(context_variant_fields),
            'context_values': context_values,
            'turn_span_values': turn_spans,
            'turn_span_min': min(turn_spans) if turn_spans else None,
            'turn_span_max': max(turn_spans) if turn_spans else None,
            'anchor_metadata_variant_fields': sorted(metadata_variant_fields),
        }
        canonical.append(item)
        if geometry_unstable:
            unsafe_geometry_groups.append(item)
        if context_variant_fields:
            context_variant_groups.append(item)
        if metadata_variant_fields:
            metadata_variant_groups.append(item)

    ambiguous_candidate_ids = {
        cid: sorted(keys)
        for cid, keys in candidate_id_to_geometry_keys.items()
        if len(keys) > 1
    }

    report = {
        'schema': 'nvt-canonical-candidate-view/0.2',
        'status': 'RESEARCH_ONLY',
        'source_candidate_dump': str(candidate_path),
        'source_id': args.source_id,
        'timeframe': args.timeframe,
        'source_row_count': len(candidates),
        'canonical_geometry_count': len(canonical),
        'collapsed_row_excess_count': len(candidates) - len(canonical),
        'unsafe_geometry_group_count': len(unsafe_geometry_groups),
        'context_variant_group_count': len(context_variant_groups),
        'anchor_metadata_variant_group_count': len(metadata_variant_groups),
        'candidate_id_with_multiple_geometry_count': len(ambiguous_candidate_ids),
        'selected_unsafe_geometry_count': sum(
            1 for x in unsafe_geometry_groups if x['selected_as_large'] or x['selected_as_mid']
        ),
        'selected_context_variant_geometry_count': sum(
            1 for x in context_variant_groups if x['selected_as_large'] or x['selected_as_mid']
        ),
        'identity_policy': {
            'geometry_identity': (
                'direction + TL anchor1 time/price + TL anchor2 time/price + '
                'CH anchor time/price + ch_offset + zone_width + slope'
            ),
            'candidate_id_role': (
                'candidate_id is a TL-family identifier, not a guaranteed unique full geometry identifier'
            ),
            'context_metrics_not_geometry': [
                'turn_span', 'tl_contacts', 'ch_contacts', 'unbroken_close'
            ],
            'anchor_confirmation_metadata_not_geometry': [
                'bar_index', 'confirmed_by_index', 'confirmed_by_time', 'retracement', 'candle'
            ],
            'scoring_guard': (
                'Score one canonical geometry once. Context variants must be represented as ranges/sets, '
                'not duplicated rows. Do not reject a geometry merely because confirmation metadata differs.'
            ),
        },
        'canonical_candidates': canonical,
        'unsafe_geometry_groups': unsafe_geometry_groups,
        'candidate_id_multiple_geometry': ambiguous_candidate_ids,
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
        'schema': report['schema'],
        'source_row_count': len(candidates),
        'canonical_geometry_count': len(canonical),
        'collapsed_row_excess_count': len(candidates) - len(canonical),
        'unsafe_geometry_group_count': len(unsafe_geometry_groups),
        'context_variant_group_count': len(context_variant_groups),
        'anchor_metadata_variant_group_count': len(metadata_variant_groups),
        'candidate_id_with_multiple_geometry_count': len(ambiguous_candidate_ids),
        'selected_unsafe_geometry_count': report['selected_unsafe_geometry_count'],
        'output': str(out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
