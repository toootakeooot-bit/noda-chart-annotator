from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Synthesize GT_0006 research-only selector lead from pre-rank and cluster-right-edge evidence.'
    )
    ap.add_argument('--selector-prerank', required=True)
    ap.add_argument('--cluster-probe', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    prerank = load_json(args.selector_prerank)
    cluster = load_json(args.cluster_probe)

    if prerank.get('case_id') != 'GT_0006' or cluster.get('case_id') != 'GT_0006':
        raise ValueError('both inputs must be GT_0006')

    gentle_recency = prerank.get('rank_views', {}).get('gentle_plus_recency_pareto_front', [])
    gentle_recency_keys = {str(x.get('candidate_key')) for x in gentle_recency}

    full_consensus = cluster.get('full_variant_consensus', [])
    consensus_by_key = {
        str(x.get('candidate', {}).get('candidate_key')): x
        for x in full_consensus
    }

    intersect = []
    for key in sorted(gentle_recency_keys & set(consensus_by_key)):
        item = consensus_by_key[key]
        intersect.append({
            'candidate': item.get('candidate'),
            'right_edge_variant_count': item.get('right_edge_variant_count'),
            'threshold_names': item.get('threshold_names'),
            'gentle_recency_pareto_member': True,
        })

    max_wick = prerank.get('wick_context', {}).get('peer_max_wick_candidate')
    max_wick_key = str((max_wick or {}).get('candidate_key'))
    for item in intersect:
        key = str(item.get('candidate', {}).get('candidate_key'))
        item['is_peer_max_wick_candidate'] = key == max_wick_key

    research_lead = None
    if len(intersect) == 1:
        research_lead = intersect[0]

    report = {
        'schema': 'nvt6-gt0006-selector-beta-research/0.1',
        'status': 'RESEARCH_ONLY',
        'case_id': 'GT_0006',
        'inputs': {
            'ownership_gate': prerank.get('ownership_gate_used'),
            'surviving_candidate_count': prerank.get('surviving_candidate_count'),
            'cluster_method': cluster.get('method'),
        },
        'evidence_intersection': {
            'gentle_recency_pareto_count': len(gentle_recency),
            'full_cluster_right_edge_consensus_count': len(full_consensus),
            'intersection_count': len(intersect),
            'intersection': intersect,
        },
        'research_lead': research_lead,
        'research_lead_status': (
            'UNIQUE_CROSS_FEATURE_RESEARCH_LEAD'
            if research_lead is not None
            else 'NO_UNIQUE_RESEARCH_LEAD'
        ),
        'wick_policy': {
            'peer_max_wick_candidate': max_wick,
            'hard_delete': False,
            'reason': (
                'Teacher evidence supports contextual wick-noise handling only. Wick remains a tag/penalty '
                'until exact visual anchor evidence is locked.'
            ),
        },
        'interpretation_guard': (
            'A unique cross-feature research lead is not a locked teacher line. GT_0006 exact anchors '
            'remain DRAFT. This report may guide visual verification and later selector scoring only; '
            'it must not write production NCA state or MT4 objects.'
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
        'research_lead_status': report['research_lead_status'],
        'research_lead': research_lead,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
