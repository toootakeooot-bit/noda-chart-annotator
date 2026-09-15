from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def in_window(value: str | None, window: list[str] | None) -> bool:
    if not value or not window or len(window) != 2:
        return False
    v = dt(value)
    lo = dt(window[0])
    hi = dt(window[1])
    assert v and lo and hi
    return lo <= v <= hi


def window_distance_seconds(value: str | None, window: list[str] | None) -> float:
    if not value or not window or len(window) != 2:
        return float('inf')
    v = dt(value)
    lo = dt(window[0])
    hi = dt(window[1])
    assert v and lo and hi
    if lo <= v <= hi:
        return 0.0
    if v < lo:
        return (lo - v).total_seconds()
    return (v - hi).total_seconds()


def compact(c: dict) -> dict:
    def p(name: str) -> dict:
        x = c.get(name) or {}
        return {
            'kind': x.get('kind'),
            'time': x.get('time'),
            'price': x.get('price'),
            'bar_index': x.get('bar_index'),
            'retracement': x.get('retracement'),
            'relevant_wick_fraction': ((x.get('candle') or {}).get('relevant_wick_fraction')),
        }

    return {
        'candidate_id': c.get('candidate_id'),
        'direction': c.get('direction'),
        'anchor1': p('anchor1'),
        'anchor2': p('anchor2'),
        'ch_anchor': p('ch_anchor'),
        'absolute_slope_per_second': c.get('absolute_slope_per_second'),
        'turn_span': c.get('turn_span'),
        'tl_contacts': c.get('tl_contacts'),
        'ch_contacts': c.get('ch_contacts'),
        'unbroken_close': c.get('unbroken_close'),
        'selected_as_large': bool(c.get('selected_as_large')),
        'selected_as_mid': bool(c.get('selected_as_mid')),
    }


def quality_key(c: dict) -> tuple:
    return (
        0 if (c.get('selected_as_large') or c.get('selected_as_mid')) else 1,
        0 if c.get('unbroken_close') else 1,
        -((c.get('tl_contacts') or 0) + (c.get('ch_contacts') or 0)),
        -(c.get('turn_span') or 0),
        c.get('absolute_slope_per_second') or float('inf'),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description='NVT5 - probe full exact Candidate Pools against video-derived Teacher anchor date windows.')
    ap.add_argument('--review-bundle', required=True)
    ap.add_argument('--hypotheses', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--max-matches', type=int, default=25)
    ap.add_argument('--max-nearest', type=int, default=12)
    args = ap.parse_args()

    bundle = load_json(args.review_bundle)
    hyp = load_json(args.hypotheses)

    candidate_paths: dict[tuple[str, str], str] = {}
    for row in bundle.get('replay_summary') or []:
        candidate_paths[(str(row.get('source_id')), str(row.get('timeframe')))] = str(row.get('candidate_dump'))

    results: list[dict[str, Any]] = []
    hard_errors: list[str] = []

    for case in hyp.get('cases') or []:
        cid = str(case.get('case_id'))
        mode = str(case.get('mode'))
        source_id = str(case.get('source_id'))
        tf = str(case.get('timeframe'))
        direction = case.get('direction')

        if mode == 'NO_LINE':
            results.append({
                'case_id': cid,
                'mode': mode,
                'status': 'NO_LINE_CONFIRMED_BY_TEACHER_EVIDENCE',
                'candidate_probe_required': False,
                'visual_hypothesis': case.get('visual_hypothesis'),
            })
            continue

        cpath_text = candidate_paths.get((source_id, tf))
        if not cpath_text:
            hard_errors.append(f'{cid}: candidate dump path not found for {source_id}/{tf}')
            continue
        cpath = Path(cpath_text)
        if not cpath.exists():
            hard_errors.append(f'{cid}: candidate dump missing: {cpath}')
            continue

        dump = load_json(cpath)
        candidates = dump.get('candidates') or []
        eligible = [c for c in candidates if not direction or c.get('direction') == direction]

        latest_anchor2 = max((dt((c.get('anchor2') or {}).get('time')) for c in eligible if (c.get('anchor2') or {}).get('time')), default=None)
        latest_anchor1 = max((dt((c.get('anchor1') or {}).get('time')) for c in eligible if (c.get('anchor1') or {}).get('time')), default=None)

        if mode == 'TL_WINDOW_PROBE':
            w1 = case.get('anchor1_window')
            w2 = case.get('anchor2_window')
            matches = [
                c for c in eligible
                if in_window((c.get('anchor1') or {}).get('time'), w1)
                and in_window((c.get('anchor2') or {}).get('time'), w2)
            ]
            matches_sorted = sorted(matches, key=quality_key)

            nearest = sorted(
                eligible,
                key=lambda c: (
                    window_distance_seconds((c.get('anchor1') or {}).get('time'), w1)
                    + window_distance_seconds((c.get('anchor2') or {}).get('time'), w2),
                    *quality_key(c),
                ),
            )[:args.max_nearest]

            results.append({
                'case_id': cid,
                'mode': mode,
                'status': 'PRESENT_WITHIN_WINDOWS' if matches else 'ABSENT_WITHIN_WINDOWS',
                'source_id': source_id,
                'timeframe': tf,
                'direction': direction,
                'anchor1_window': w1,
                'anchor2_window': w2,
                'eligible_candidate_count': len(eligible),
                'window_match_count': len(matches),
                'latest_anchor1_time_in_direction': latest_anchor1.isoformat() if latest_anchor1 else None,
                'latest_anchor2_time_in_direction': latest_anchor2.isoformat() if latest_anchor2 else None,
                'matches': [compact(c) for c in matches_sorted[:args.max_matches]],
                'nearest_when_window_not_exact': [compact(c) for c in nearest],
                'visual_hypothesis': case.get('visual_hypothesis'),
                'confidence': case.get('confidence'),
                'interpretation_rule': 'Window presence is only a Candidate-generation diagnostic. It is not a Teacher-match lock.',
            })

        elif mode == 'CH_LIFECYCLE_PROBE':
            w1 = case.get('parent_anchor1_window')
            w2 = case.get('parent_anchor2_window')
            parent_matches = [
                c for c in eligible
                if in_window((c.get('anchor1') or {}).get('time'), w1)
                and in_window((c.get('anchor2') or {}).get('time'), w2)
            ]
            parent_matches = sorted(parent_matches, key=quality_key)
            unique_ch = {}
            for c in parent_matches:
                ch = c.get('ch_anchor') or {}
                key = (ch.get('time'), ch.get('price'))
                if key not in unique_ch:
                    unique_ch[key] = compact(c)

            results.append({
                'case_id': cid,
                'mode': mode,
                'status': 'PARENT_GEOMETRY_PRESENT' if parent_matches else 'PARENT_GEOMETRY_ABSENT',
                'source_id': source_id,
                'timeframe': tf,
                'direction': direction,
                'parent_anchor1_window': w1,
                'parent_anchor2_window': w2,
                'eligible_candidate_count': len(eligible),
                'parent_window_match_count': len(parent_matches),
                'distinct_ch_anchor_count_for_parent_window': len(unique_ch),
                'parent_matches': [compact(c) for c in parent_matches[:args.max_matches]],
                'distinct_ch_examples': list(unique_ch.values())[:args.max_matches],
                'visual_hypothesis': case.get('visual_hypothesis'),
                'confidence': case.get('confidence'),
                'interpretation_rule': 'This probe can show whether multiple CH geometries exist for the Teacher-like parent TL window, but KEEP/REFERENCE/CURRENT remains a Lifecycle judgment.',
            })
        else:
            hard_errors.append(f'{cid}: unsupported mode {mode}')

    payload = {
        'schema': 'nvt5-teacher-anchor-window-probe/1.0',
        'status': 'PASS' if not hard_errors else 'FAIL',
        'purpose': 'Candidate-generation diagnostic against video-derived visual anchor windows; no Ground Truth mutation.',
        'review_bundle_status': bundle.get('status'),
        'hypothesis_status': hyp.get('status'),
        'results': results,
        'hard_errors': hard_errors,
        'safety': {
            'ground_truth_writeback': False,
            'selector_writeback': False,
            'production_writeback': False,
            'mt4_writeback': False,
            'trade_authority': False,
        },
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'status': payload['status'],
        'output': str(out),
        'case_statuses': {r.get('case_id'): r.get('status') for r in results},
        'hard_error_count': len(hard_errors),
    }, ensure_ascii=True, indent=2))
    return 0 if payload['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
