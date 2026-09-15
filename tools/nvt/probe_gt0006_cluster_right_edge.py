from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def quantile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError('quantile requires at least one value')
    xs = sorted(float(x) for x in values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(str(value))


def slim(row: dict) -> dict:
    return {
        'candidate_key': row.get('candidate_key'),
        'anchor2_time': row.get('anchor2_time'),
        'anchor2_price': row.get('anchor2_price'),
        'gentle_slope_rank_within_origin': row.get('gentle_slope_rank_within_origin'),
        'anchor2_recency_rank_within_origin': row.get('anchor2_recency_rank_within_origin'),
        'anchor2_low_wick_rank_within_origin': row.get('anchor2_low_wick_rank_within_origin'),
        'anchor2_wick_fraction_of_range': row.get('anchor2_wick_fraction_of_range'),
        'absolute_slope_per_hour': row.get('absolute_slope_per_hour'),
        'elapsed_hours': row.get('elapsed_hours'),
    }


def nearest_neighbor_distances(rows: list[dict]) -> list[float]:
    prices = [float(r['anchor2_price']) for r in rows]
    out = []
    for i, price in enumerate(prices):
        peers = [abs(price - other) for j, other in enumerate(prices) if j != i]
        if peers:
            out.append(min(peers))
    return out


def cluster_by_price(rows: list[dict], threshold: float) -> list[list[dict]]:
    ordered = sorted(rows, key=lambda r: (float(r['anchor2_price']), str(r['anchor2_time'])))
    if not ordered:
        return []
    groups: list[list[dict]] = [[ordered[0]]]
    for row in ordered[1:]:
        prev = groups[-1][-1]
        gap = float(row['anchor2_price']) - float(prev['anchor2_price'])
        if gap <= threshold + 1e-12:
            groups[-1].append(row)
        else:
            groups.append([row])
    return groups


def cluster_record(group: list[dict], threshold_name: str, threshold: float) -> dict:
    latest = max(group, key=lambda r: parse_dt(r['anchor2_time']))
    prices = [float(r['anchor2_price']) for r in group]
    return {
        'threshold_name': threshold_name,
        'threshold': threshold,
        'cluster_size': len(group),
        'price_min': min(prices),
        'price_max': max(prices),
        'price_span': max(prices) - min(prices),
        'members': [slim(r) for r in sorted(group, key=lambda r: parse_dt(r['anchor2_time']))],
        'right_edge_candidate': slim(latest),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Probe GT_0006 cluster-right-edge under data-driven price-cluster sensitivity variants.'
    )
    ap.add_argument('--gate-report', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    gate = load_json(args.gate_report)
    case = gate.get('cases', {}).get('GT_0006')
    if not case:
        raise ValueError('GT_0006 missing from gate report')

    rows = [r for r in case.get('candidates', []) if r.get('gate_C_A_and_B') is True]
    if len(rows) < 2:
        raise ValueError('need at least two gate-C GT_0006 candidates')

    nn = nearest_neighbor_distances(rows)
    q50 = quantile(nn, 0.50)
    q75 = quantile(nn, 0.75)
    variants = [
        ('NN_Q50', q50),
        ('NN_Q75', q75),
        ('NN_Q75_X2', q75 * 2.0),
    ]

    variant_reports = []
    consensus: dict[str, dict] = {}
    for name, threshold in variants:
        clusters = [g for g in cluster_by_price(rows, threshold) if len(g) >= 2]
        recs = [cluster_record(g, name, threshold) for g in clusters]
        variant_reports.append({
            'threshold_name': name,
            'threshold': threshold,
            'cluster_count_min_size_2': len(recs),
            'clusters': recs,
        })
        for rec in recs:
            cand = rec['right_edge_candidate']
            key = str(cand['candidate_key'])
            slot = consensus.setdefault(key, {
                'candidate': cand,
                'right_edge_variant_count': 0,
                'threshold_names': [],
            })
            slot['right_edge_variant_count'] += 1
            slot['threshold_names'].append(name)

    consensus_rows = sorted(
        consensus.values(),
        key=lambda x: (
            -int(x['right_edge_variant_count']),
            int(x['candidate'].get('gentle_slope_rank_within_origin') or 10**9),
            int(x['candidate'].get('anchor2_recency_rank_within_origin') or 10**9),
        ),
    )
    variant_count = len(variants)
    full_consensus = [x for x in consensus_rows if x['right_edge_variant_count'] == variant_count]
    gentle_first_full_consensus = [
        x for x in full_consensus
        if int(x['candidate'].get('gentle_slope_rank_within_origin') or 10**9) == 1
    ]

    report = {
        'schema': 'nvt6-gt0006-cluster-right-edge-probe/0.1',
        'status': 'RESEARCH_ONLY',
        'case_id': 'GT_0006',
        'ownership_gate_used': 'C_A_AND_B',
        'candidate_count': len(rows),
        'method': {
            'cluster_axis': 'anchor2_price',
            'clustering': 'single-link adjacent price gaps',
            'minimum_cluster_size': 2,
            'right_edge_definition': 'latest anchor2_time inside a price cluster',
            'threshold_source': 'data-driven nearest-neighbor anchor2 price distances',
            'threshold_variants': [
                {'name': n, 'value': v} for n, v in variants
            ],
            'nearest_neighbor_distance_summary': {
                'min': min(nn),
                'median_q50': q50,
                'q75': q75,
                'max': max(nn),
            },
        },
        'variant_reports': variant_reports,
        'right_edge_consensus': consensus_rows,
        'full_variant_consensus': full_consensus,
        'gentle_rank1_and_full_variant_consensus': gentle_first_full_consensus,
        'interpretation_guard': (
            'This is a sensitivity probe, not a fixed teacher cluster definition. A candidate that '
            'is the right edge under all tested data-driven thresholds is only a research lead. '
            'Exact GT_0006 visual anchors remain DRAFT and must be checked before hard regression use.'
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
        'candidate_count': len(rows),
        'thresholds': report['method']['threshold_variants'],
        'full_consensus_count': len(full_consensus),
        'gentle_rank1_full_consensus': gentle_first_full_consensus,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
