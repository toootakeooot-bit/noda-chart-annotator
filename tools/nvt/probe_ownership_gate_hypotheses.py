from __future__ import annotations

import argparse
import json
from pathlib import Path


PRICE_TOLERANCE = 1e-6
TARGET_CASES = ('GT_0006', 'GT_0007')


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def price_match(a, b, tol: float = PRICE_TOLERANCE) -> bool:
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= tol


def evaluate_candidate(row: dict) -> dict:
    higher = row.get('higher_timeframe_context', {})
    a1_price = row.get('anchor1_price')

    direction_consensus = {}
    anchor_ownership = {}
    for tf in ('H4', 'D1'):
        ctx = higher.get(tf, {})
        cutoff = ctx.get('at_cutoff', {})
        direction_consensus[tf] = cutoff.get('direction_agrees') is True
        latest_same = cutoff.get('latest_same_side_pivot') or {}
        anchor_ownership[tf] = price_match(a1_price, latest_same.get('price'))

    gate_a = all(direction_consensus.values())
    gate_b = all(anchor_ownership.values())
    gate_c = gate_a and gate_b

    return {
        'candidate_key': row.get('candidate_key'),
        'direction': row.get('direction'),
        'provenance': row.get('provenance'),
        'anchor1_time': row.get('anchor1_time'),
        'anchor1_price': a1_price,
        'anchor2_time': row.get('anchor2_time'),
        'anchor2_price': row.get('anchor2_price'),
        'gate_A_h4_d1_direction_consensus_at_cutoff': gate_a,
        'gate_B_h4_d1_anchor_ownership_at_cutoff': gate_b,
        'gate_C_A_and_B': gate_c,
        'direction_consensus_detail': direction_consensus,
        'anchor_ownership_detail': anchor_ownership,
        'gentle_slope_rank_within_origin': row.get('gentle_slope_rank_within_origin'),
        'anchor2_recency_rank_within_origin': row.get('anchor2_recency_rank_within_origin'),
        'anchor2_low_wick_rank_within_origin': row.get('anchor2_low_wick_rank_within_origin'),
        'anchor2_wick_fraction_of_range': row.get('anchor2_wick_fraction_of_range'),
        'absolute_slope_per_hour': row.get('absolute_slope_per_hour'),
        'elapsed_hours': row.get('elapsed_hours'),
    }


def summarize_case(case_id: str, case: dict) -> dict:
    evaluated = [evaluate_candidate(r) for r in case.get('features', [])]

    def count(field: str) -> int:
        return sum(1 for r in evaluated if r[field])

    return {
        'case_id': case_id,
        'source_id': case.get('source_id'),
        'timeframe': case.get('timeframe'),
        'exact_cutoff': case.get('exact_cutoff'),
        'input_candidate_count': len(evaluated),
        'gate_counts': {
            'A_H4_D1_DIRECTION_CONSENSUS_AT_CUTOFF': count(
                'gate_A_h4_d1_direction_consensus_at_cutoff'
            ),
            'B_H4_D1_ANCHOR_OWNERSHIP_AT_CUTOFF': count(
                'gate_B_h4_d1_anchor_ownership_at_cutoff'
            ),
            'C_A_AND_B': count('gate_C_A_and_B'),
        },
        'candidates': evaluated,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Compare NVT6 ownership-gate hypotheses A/B/C on GT_0006 and GT_0007.'
    )
    ap.add_argument('--feature-probe', required=True)
    ap.add_argument('--gt0005-precheck', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    features = load_json(args.feature_probe)
    precheck = load_json(args.gt0005_precheck)
    if precheck.get('status') != 'PASS':
        raise ValueError('GT_0005 display-suppression precheck must PASS before gate research')
    if precheck.get('semantic_classification', {}).get('ownership_negative') is not False:
        raise ValueError('GT_0005 must not be treated as an ownership negative')

    cases = features.get('cases', {})
    missing = [cid for cid in TARGET_CASES if cid not in cases]
    if missing:
        raise ValueError(f'missing cases in feature probe: {missing}')

    result_cases = {cid: summarize_case(cid, cases[cid]) for cid in TARGET_CASES}
    g6 = result_cases['GT_0006']['gate_counts']
    g7 = result_cases['GT_0007']['gate_counts']

    hypotheses = {
        'A_H4_D1_DIRECTION_CONSENSUS_AT_CUTOFF': {
            'gt0006_pass_count': g6['A_H4_D1_DIRECTION_CONSENSUS_AT_CUTOFF'],
            'gt0007_pass_count': g7['A_H4_D1_DIRECTION_CONSENSUS_AT_CUTOFF'],
        },
        'B_H4_D1_ANCHOR_OWNERSHIP_AT_CUTOFF': {
            'gt0006_pass_count': g6['B_H4_D1_ANCHOR_OWNERSHIP_AT_CUTOFF'],
            'gt0007_pass_count': g7['B_H4_D1_ANCHOR_OWNERSHIP_AT_CUTOFF'],
        },
        'C_A_AND_B': {
            'gt0006_pass_count': g6['C_A_AND_B'],
            'gt0007_pass_count': g7['C_A_AND_B'],
        },
    }
    for item in hypotheses.values():
        item['separates_current_positive_and_negative_control'] = bool(
            item['gt0006_pass_count'] > 0 and item['gt0007_pass_count'] == 0
        )

    report = {
        'schema': 'nvt6-ownership-gate-hypotheses/0.1',
        'status': 'RESEARCH_ONLY',
        'mode': 'NO_PRODUCTION_WRITEBACK',
        'price_match_tolerance': PRICE_TOLERANCE,
        'gt0005_precondition': {
            'processed_first': True,
            'valid_display_suppressed_line': True,
            'used_as_ownership_negative': False,
        },
        'hypothesis_definitions': {
            'A': (
                'At the teacher-decision cutoff, candidate direction agrees with both H4 and D1 '
                'active legs.'
            ),
            'B': (
                'At the teacher-decision cutoff, candidate anchor1 price matches the latest '
                'same-side structural pivot price on both H4 and D1. Time equality is not required '
                'because higher-timeframe bar opens differ.'
            ),
            'C': 'A and B are both true.',
        },
        'cases': result_cases,
        'hypothesis_results': hypotheses,
        'interpretation_guard': (
            'A/B/C are research hypotheses only. Separation of one positive case (GT_0006) and '
            'one timeframe-global negative control (GT_0007) is not sufficient to fix a production '
            'ownership rule. GT_0005 is deliberately excluded as a negative because it is a valid '
            'line that is hidden for lifecycle/clutter reasons.'
        ),
        'next_step_if_separation_holds': (
            'Use surviving GT_0006 candidates for selector pre-ranking; then regress the gate '
            'against additional positive/negative Ground Truth cases before any production promotion.'
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
        'hypothesis_results': hypotheses,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
