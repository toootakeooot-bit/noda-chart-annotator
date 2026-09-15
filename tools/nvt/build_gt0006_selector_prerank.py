from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def pareto_front(rows: list[dict], rank_fields: tuple[str, ...]) -> list[dict]:
    front = []
    for row in rows:
        dominated = False
        for other in rows:
            if other is row:
                continue
            no_worse = all(
                int(other.get(f) or 10**9) <= int(row.get(f) or 10**9)
                for f in rank_fields
            )
            strictly_better = any(
                int(other.get(f) or 10**9) < int(row.get(f) or 10**9)
                for f in rank_fields
            )
            if no_worse and strictly_better:
                dominated = True
                break
        if not dominated:
            front.append(row)
    return front


def slim(row: dict) -> dict:
    return {
        'candidate_key': row.get('candidate_key'),
        'anchor1_time': row.get('anchor1_time'),
        'anchor1_price': row.get('anchor1_price'),
        'anchor2_time': row.get('anchor2_time'),
        'anchor2_price': row.get('anchor2_price'),
        'gentle_slope_rank_within_origin': row.get('gentle_slope_rank_within_origin'),
        'anchor2_recency_rank_within_origin': row.get('anchor2_recency_rank_within_origin'),
        'anchor2_low_wick_rank_within_origin': row.get('anchor2_low_wick_rank_within_origin'),
        'anchor2_wick_fraction_of_range': row.get('anchor2_wick_fraction_of_range'),
        'absolute_slope_per_hour': row.get('absolute_slope_per_hour'),
        'elapsed_hours': row.get('elapsed_hours'),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Pre-rank GT_0006 selector features after research ownership gating.'
    )
    ap.add_argument('--gate-report', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    gate = load_json(args.gate_report)
    case = gate.get('cases', {}).get('GT_0006')
    if not case:
        raise ValueError('GT_0006 missing from gate report')

    candidates = [
        r for r in case.get('candidates', [])
        if r.get('gate_C_A_and_B') is True
    ]
    if not candidates:
        raise ValueError('no GT_0006 candidates survive gate C')

    by_gentle = sorted(
        candidates,
        key=lambda r: (int(r.get('gentle_slope_rank_within_origin') or 10**9), r.get('candidate_key') or ''),
    )
    by_recency = sorted(
        candidates,
        key=lambda r: (int(r.get('anchor2_recency_rank_within_origin') or 10**9), r.get('candidate_key') or ''),
    )
    by_low_wick = sorted(
        candidates,
        key=lambda r: (int(r.get('anchor2_low_wick_rank_within_origin') or 10**9), r.get('candidate_key') or ''),
    )
    by_wick_fraction_desc = sorted(
        candidates,
        key=lambda r: float(r.get('anchor2_wick_fraction_of_range') or -1.0),
        reverse=True,
    )

    gentle_recency_front = pareto_front(
        candidates,
        ('gentle_slope_rank_within_origin', 'anchor2_recency_rank_within_origin'),
    )
    all_three_front = pareto_front(
        candidates,
        (
            'gentle_slope_rank_within_origin',
            'anchor2_recency_rank_within_origin',
            'anchor2_low_wick_rank_within_origin',
        ),
    )

    report = {
        'schema': 'nvt6-gt0006-selector-prerank/0.1',
        'status': 'RESEARCH_ONLY',
        'case_id': 'GT_0006',
        'ownership_gate_used': 'C_A_AND_B',
        'surviving_candidate_count': len(candidates),
        'rank_views': {
            'gentle_slope_top5': [slim(r) for r in by_gentle[:5]],
            'anchor2_recency_top5': [slim(r) for r in by_recency[:5]],
            'low_wick_top5': [slim(r) for r in by_low_wick[:5]],
            'gentle_plus_recency_pareto_front': [slim(r) for r in gentle_recency_front],
            'gentle_recency_wick_pareto_front': [slim(r) for r in all_three_front],
        },
        'wick_context': {
            'peer_max_wick_candidate': slim(by_wick_fraction_desc[0]),
            'peer_min_wick_candidate': slim(by_low_wick[0]),
            'policy': (
                'Wick is evidence for penalty/tag only. Do not hard-delete candidates from this '
                'pre-rank because teacher evidence only says an unusually long wick may be noise.'
            ),
        },
        'cluster_right_edge_status': {
            'implemented': False,
            'reason': (
                'Anchor2 recency rank is not equivalent to teacher cluster-right-edge. A separate '
                'evidence-driven cluster definition is still required before final selector scoring.'
            ),
        },
        'interpretation_guard': (
            'This report does not select the teacher line. Exact GT_0006 anchors remain DRAFT. '
            'A candidate that ranks first on gentle slope and recency is only a research lead until '
            'cluster-right-edge and visual anchor evidence are confirmed.'
        ),
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
        'surviving_candidate_count': len(candidates),
        'gentle_slope_first': slim(by_gentle[0]),
        'recency_first': slim(by_recency[0]),
        'peer_max_wick': slim(by_wick_fraction_desc[0]),
        'cluster_right_edge_implemented': False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
