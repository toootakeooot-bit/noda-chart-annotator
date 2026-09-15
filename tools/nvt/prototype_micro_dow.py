from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def slope_per_hour(t1: datetime, p1: float, t2: datetime, p2: float) -> float:
    hours = (t2 - t1).total_seconds() / 3600.0
    if hours <= 0:
        raise ValueError('anchor2 must be later than anchor1')
    return (p2 - p1) / hours


def in_window(value: str, start: str, end: str) -> bool:
    t = dt(value)
    return dt(start) <= t <= dt(end)


def main() -> int:
    ap = argparse.ArgumentParser(
        description='NVT research-only micro-Dow candidate prototype for GT_0006.'
    )
    ap.add_argument('--diagnostic', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    src = Path(args.diagnostic)
    payload = json.loads(src.read_text(encoding='utf-8'))
    if payload.get('case_id') != 'GT_0006':
        raise ValueError('expected GT_0006 diagnostic')

    windows = payload['teacher_anchor_windows']
    a1w = windows['anchor1']
    a2w = windows['anchor2']
    highs = payload['local_highs']

    # Research layer only: a local rebound high is structurally validated when
    # the next local low breaks the preceding local low.  L2/R2 is used as a
    # stricter noise filter, not as a production rule.
    def structurally_valid(row: dict) -> bool:
        return bool(row['micro_dow_context'].get('next_low_breaks_previous_low'))

    def strict(row: dict) -> bool:
        return structurally_valid(row) and bool(row.get('is_l2r2_local_high'))

    a1_confirmed = [
        r for r in highs
        if in_window(r['time'], a1w['start'], a1w['end'])
        and r.get('production_confirmed_high')
    ]
    a1_micro = [
        r for r in highs
        if in_window(r['time'], a1w['start'], a1w['end']) and strict(r)
    ]
    a2_micro = [
        r for r in highs
        if in_window(r['time'], a2w['start'], a2w['end']) and strict(r)
    ]

    pair_rows: list[dict] = []
    anchor1_union = []
    seen = set()
    for row in a1_confirmed + a1_micro:
        key = row['time']
        if key not in seen:
            seen.add(key)
            anchor1_union.append(row)

    for a in anchor1_union:
        t1, p1 = dt(a['time']), float(a['high'])
        for b in a2_micro:
            t2, p2 = dt(b['time']), float(b['high'])
            if t2 <= t1 or p2 >= p1:
                continue
            slope = slope_per_hour(t1, p1, t2, p2)
            pair_rows.append({
                'layer': 'MICRO_DOW_RESEARCH',
                'direction': 'FALLING',
                'anchor1_time': a['time'],
                'anchor1_high': p1,
                'anchor1_production_confirmed': bool(a.get('production_confirmed_high')),
                'anchor1_strict_micro': strict(a),
                'anchor2_time': b['time'],
                'anchor2_high': p2,
                'anchor2_production_confirmed': bool(b.get('production_confirmed_high')),
                'anchor2_strict_micro': strict(b),
                'elapsed_hours': (t2 - t1).total_seconds() / 3600.0,
                'slope_per_hour': slope,
                'absolute_slope_per_hour': abs(slope),
                'candidate_key': f"MICRO:FALLING:{a['time']}:{b['time']}",
            })

    # Preserve alternatives.  Ranking is diagnostic only; no winner is selected.
    gentle = sorted(
        pair_rows,
        key=lambda r: (r['absolute_slope_per_hour'], -r['elapsed_hours'])
    )

    confirmed_origin_pairs = [
        r for r in pair_rows if r['anchor1_production_confirmed']
    ]
    confirmed_origin_gentle = sorted(
        confirmed_origin_pairs,
        key=lambda r: (r['absolute_slope_per_hour'], -r['elapsed_hours'])
    )

    out_payload = {
        'schema': 'nvt-micro-dow-prototype/0.1',
        'status': 'RESEARCH_ONLY',
        'case_id': 'GT_0006',
        'source_diagnostic': str(src),
        'purpose': (
            'Test whether a separate nested micro-Dow layer restores teacher-like '
            'H1 descending TL anchor alternatives without weakening production 38% pivots.'
        ),
        'rules': {
            'production_38_detector_unchanged': True,
            'micro_high_structural_confirmation': 'LOW -> rebound HIGH -> LOWER LOW',
            'strict_noise_filter': 'local high must also satisfy L2/R2 local-extrema lens',
            'auto_select_teacher_line': False,
            'production_writeback': False,
        },
        'counts': {
            'anchor1_confirmed_count': len(a1_confirmed),
            'anchor1_strict_micro_count': len(a1_micro),
            'anchor2_strict_micro_count': len(a2_micro),
            'falling_micro_pair_count': len(pair_rows),
            'falling_pairs_from_production_confirmed_anchor1': len(confirmed_origin_pairs),
        },
        'anchor1_candidates': [
            {
                'time': r['time'],
                'high': r['high'],
                'production_confirmed': r['production_confirmed_high'],
                'strict_micro': strict(r),
            }
            for r in anchor1_union
        ],
        'anchor2_strict_micro_candidates': [
            {
                'time': r['time'],
                'high': r['high'],
                'production_confirmed': r['production_confirmed_high'],
                'diagnostic_reason': r['diagnostic_reason'],
            }
            for r in a2_micro
        ],
        'gentlest_pairs_overall_top20': gentle[:20],
        'gentlest_pairs_from_confirmed_anchor1_top20': confirmed_origin_gentle[:20],
        'all_pairs': pair_rows,
        'interpretation_guard': (
            'A recovered micro pair proves candidate recall only. It does not prove '
            'the teacher would draw that pair, and it must not bypass NO-LINE / '
            'structure-ownership validation such as GT_0005 and GT_0007.'
        ),
        'production_writeback': False,
        'normal_run_modified': False,
        'mt4_object_writeback': False,
        'trade_authority': False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'status': 'PASS',
        'output': str(out),
        **out_payload['counts'],
        'production_modified': False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
