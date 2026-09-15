from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def norm_direction(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().upper()
    if value in {'UP', 'RISING', 'BULL', 'BULLISH'}:
        return 'RISING'
    if value in {'DOWN', 'FALLING', 'BEAR', 'BEARISH'}:
        return 'FALLING'
    return value


def compact_candidate(c: dict, reasons: list[str]) -> dict:
    def pivot(name: str) -> dict:
        p = c.get(name) or {}
        candle = p.get('candle') or {}
        return {
            'kind': p.get('kind'),
            'bar_index': p.get('bar_index'),
            'time': p.get('time'),
            'price': p.get('price'),
            'retracement': p.get('retracement'),
            'relevant_wick_fraction': candle.get('relevant_wick_fraction'),
        }

    return {
        'candidate_id': c.get('candidate_id'),
        'review_reasons': sorted(set(reasons)),
        'direction': c.get('direction'),
        'anchor1': pivot('anchor1'),
        'anchor2': pivot('anchor2'),
        'ch_anchor': pivot('ch_anchor'),
        'absolute_slope_per_second': c.get('absolute_slope_per_second'),
        'turn_span': c.get('turn_span'),
        'tl_contacts': c.get('tl_contacts'),
        'ch_contacts': c.get('ch_contacts'),
        'unbroken_close': c.get('unbroken_close'),
        'selected_as_large': bool(c.get('selected_as_large')),
        'selected_as_mid': bool(c.get('selected_as_mid')),
    }


def add_ranked(reason_map: dict[str, list[str]], rows: list[dict], reason: str, limit: int) -> None:
    for c in rows[:limit]:
        cid = str(c.get('candidate_id'))
        reason_map[cid].append(reason)


def main() -> int:
    ap = argparse.ArgumentParser(
        description='NVT5 - build a neutral candidate shortlist for human Teacher-anchor review.'
    )
    ap.add_argument('--ground-truth', required=True)
    ap.add_argument('--candidate-dump', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--per-view', type=int, default=6)
    args = ap.parse_args()

    if args.per_view < 1:
        raise ValueError('per-view must be >= 1')

    gt = load_json(args.ground_truth)
    dump = load_json(args.candidate_dump)
    candidates = dump.get('candidates') or []
    teacher_objects = gt.get('teacher_objects') or []

    payload = {
        'schema': 'nvt-anchor-review-workbench/1.0',
        'mode': 'HUMAN_REVIEW_AID_ONLY',
        'case_id': gt.get('case_id'),
        'source_id': gt.get('source_id'),
        'teacher_symbol': gt.get('symbol'),
        'broker_symbol': dump.get('symbol'),
        'timeframe': gt.get('timeframe'),
        'effective_last_closed_bar': dump.get('effective_last_closed_bar'),
        'expected_no_line': len(teacher_objects) == 0,
        'baseline_selected_large_candidate_id': dump.get('selected_large_candidate_id'),
        'baseline_selected_mid_candidate_id': dump.get('selected_mid_candidate_id'),
        'teacher_objects': [],
        'rules': {
            'does_not_choose_teacher_match': True,
            'does_not_modify_ground_truth': True,
            'does_not_modify_selector': True,
            'purpose': 'reduce candidate-review workload while preserving multiple plausible geometries',
        },
    }

    if not teacher_objects:
        payload['no_line_review'] = {
            'selected_candidate_ids': [
                x for x in (
                    dump.get('selected_large_candidate_id'),
                    dump.get('selected_mid_candidate_id'),
                ) if x
            ],
            'candidate_count': len(candidates),
            'note': 'Teacher expects no line on this timeframe. Candidate geometry is not treated as a Teacher match.',
        }
    else:
        by_id = {str(c.get('candidate_id')): c for c in candidates}
        for obj in teacher_objects:
            direction = norm_direction(obj.get('direction'))
            eligible = [c for c in candidates if not direction or c.get('direction') == direction]
            reasons: dict[str, list[str]] = defaultdict(list)

            selected = [c for c in eligible if c.get('selected_as_large') or c.get('selected_as_mid')]
            add_ranked(reasons, selected, 'BASELINE_SELECTED', args.per_view)

            add_ranked(
                reasons,
                sorted(eligible, key=lambda c: (-(c.get('turn_span') or 0), c.get('absolute_slope_per_second') or 0)),
                'LONG_STRUCTURE_SPAN', args.per_view,
            )
            add_ranked(
                reasons,
                sorted(
                    eligible,
                    key=lambda c: (
                        -((c.get('tl_contacts') or 0) + (c.get('ch_contacts') or 0)),
                        -(c.get('tl_contacts') or 0),
                        -(c.get('ch_contacts') or 0),
                    ),
                ),
                'HIGH_CONTACT_QUALITY', args.per_view,
            )
            add_ranked(
                reasons,
                sorted(eligible, key=lambda c: c.get('absolute_slope_per_second') or float('inf')),
                'GENTLE_SLOPE', args.per_view,
            )
            add_ranked(
                reasons,
                sorted(
                    eligible,
                    key=lambda c: -int(((c.get('anchor2') or {}).get('bar_index')) or -1),
                ),
                'RECENT_ANCHOR2', args.per_view,
            )
            unbroken = [c for c in eligible if c.get('unbroken_close')]
            add_ranked(
                reasons,
                sorted(unbroken, key=lambda c: -(c.get('turn_span') or 0)),
                'UNBROKEN_CLOSE_EVIDENCE', args.per_view,
            )

            shortlist = []
            for cid, why in reasons.items():
                c = by_id.get(cid)
                if c is not None:
                    shortlist.append(compact_candidate(c, why))
            shortlist.sort(
                key=lambda r: (
                    0 if (r['selected_as_large'] or r['selected_as_mid']) else 1,
                    -len(r['review_reasons']),
                    -(r['turn_span'] or 0),
                )
            )

            payload['teacher_objects'].append({
                'teacher_object_id': obj.get('object_id'),
                'object_type': obj.get('object_type'),
                'teacher_role': obj.get('teacher_role'),
                'teacher_direction': direction,
                'teacher_anchor1_time': obj.get('anchor1_time'),
                'teacher_anchor2_time': obj.get('anchor2_time'),
                'eligible_candidate_count': len(eligible),
                'shortlist_count': len(shortlist),
                'shortlist': shortlist,
            })

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'status': 'PASS',
        'case_id': payload['case_id'],
        'expected_no_line': payload['expected_no_line'],
        'teacher_object_count': len(payload['teacher_objects']),
        'output': str(out),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
