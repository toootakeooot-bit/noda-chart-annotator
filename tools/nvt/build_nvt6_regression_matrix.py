from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def gt_case(gt_dir: Path, case_id: str) -> dict:
    return load_json(gt_dir / f'{case_id}.json')


def main() -> int:
    ap = argparse.ArgumentParser(description='Build a research-only NVT6 soft regression matrix.')
    ap.add_argument('--ground-truth-dir', required=True)
    ap.add_argument('--gt0005-precheck', required=True)
    ap.add_argument('--gate-report', required=True)
    ap.add_argument('--cluster-report', required=True)
    ap.add_argument('--selector-beta', required=True)
    ap.add_argument('--gt0003-canonical', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    gt_dir = Path(args.ground_truth_dir)
    gt1 = gt_case(gt_dir, 'GT_0001')
    gt3 = gt_case(gt_dir, 'GT_0003')
    gt5 = gt_case(gt_dir, 'GT_0005')
    gt6 = gt_case(gt_dir, 'GT_0006')
    gt7 = gt_case(gt_dir, 'GT_0007')

    pre5 = load_json(args.gt0005_precheck)
    gate = load_json(args.gate_report)
    cluster = load_json(args.cluster_report)
    selector = load_json(args.selector_beta)
    canonical3 = load_json(args.gt0003_canonical)

    g5 = pre5.get('semantic_classification', {})
    gate6 = gate.get('cases', {}).get('GT_0006', {})
    gate7 = gate.get('cases', {}).get('GT_0007', {})
    c6 = gate6.get('gate_counts', {}).get('C_A_AND_B')
    c7 = gate7.get('gate_counts', {}).get('C_A_AND_B')
    lead = selector.get('research_lead')

    gt1_exact_locked = bool(
        gt1.get('annotation_status') == 'LOCKED'
        and gt1.get('teacher_objects')
        and gt1['teacher_objects'][0].get('anchor1_time') not in {None, 'UNKNOWN'}
        and gt1['teacher_objects'][0].get('anchor2_time') not in {None, 'UNKNOWN'}
    )
    gt3_exact_locked = bool(
        gt3.get('annotation_status') == 'LOCKED'
        and gt3.get('teacher_objects')
        and gt3['teacher_objects'][0].get('anchor1_time') not in {None, 'UNKNOWN'}
        and gt3['teacher_objects'][0].get('anchor2_time') not in {None, 'UNKNOWN'}
    )
    gt6_exact_locked = bool(
        gt6.get('annotation_status') == 'LOCKED'
        and gt6.get('teacher_objects')
        and gt6['teacher_objects'][0].get('anchor1_time') not in {None, 'UNKNOWN'}
        and gt6['teacher_objects'][0].get('anchor2_time') not in {None, 'UNKNOWN'}
    )

    matrix = [
        {
            'case_id': 'GT_0001',
            'role': 'POSITIVE_SELECTOR_CLUSTER_RIGHT_EDGE_EVIDENCE',
            'timeframe': gt1.get('timeframe'),
            'source_interval': gt1.get('source_locator', {}),
            'soft_status': 'PENDING_EXACT_ANCHOR_LOCK' if not gt1_exact_locked else 'HARD_REGRESSION_ELIGIBLE',
            'current_use': 'Defines teacher evidence for lowest-low to relevant-cluster-right-edge behavior. Do not score an exact candidate until anchors are locked.',
            'blocks_nvt6_research': False,
            'blocks_production_promotion': not gt1_exact_locked,
        },
        {
            'case_id': 'GT_0003',
            'role': 'POSITIVE_WICK_CONTEXT_CONTROL',
            'timeframe': gt3.get('timeframe'),
            'source_interval': gt3.get('source_locator', {}),
            'soft_status': 'PENDING_EXACT_ANCHOR_LOCK' if not gt3_exact_locked else 'HARD_REGRESSION_ELIGIBLE',
            'canonical_candidate_view_status': canonical3.get('status'),
            'canonical_unsafe_geometry_group_count': canonical3.get('unsafe_geometry_group_count'),
            'current_use': 'Prevents hard wick deletion and checks candidate identity normalization. Exact wick-to-wick geometry remains draft.',
            'blocks_nvt6_research': False,
            'blocks_production_promotion': not gt3_exact_locked,
        },
        {
            'case_id': 'GT_0005',
            'role': 'VALID_BUT_DISPLAY_SUPPRESSED_TURN_LINE',
            'timeframe': gt5.get('timeframe'),
            'source_interval': gt5.get('source_locator', {}),
            'soft_status': 'PASS_SEMANTIC_GUARD' if (
                g5.get('candidate_valid') is True
                and g5.get('display_suppressed') is True
                and g5.get('ownership_negative') is False
                and g5.get('invalid_line') is False
            ) else 'FAIL_SEMANTIC_GUARD',
            'current_use': 'Must be processed before GT_0006 so valid steep small-Dow turn lines are not learned as ownership negatives.',
            'blocks_nvt6_research': False,
            'blocks_production_promotion': True,
            'production_block_reason': 'Exact anchors/lifecycle visibility thresholds are not quantified yet.',
        },
        {
            'case_id': 'GT_0006',
            'role': 'POSITIVE_H1_SELECTOR_CASE',
            'timeframe': gt6.get('timeframe'),
            'source_interval': gt6.get('source_locator', {}),
            'soft_status': 'UNIQUE_RESEARCH_LEAD_PENDING_VISUAL_LOCK' if (
                selector.get('research_lead_status') == 'UNIQUE_CROSS_FEATURE_RESEARCH_LEAD'
                and lead
                and c6 == 13
            ) else 'RESEARCH_LEAD_UNRESOLVED',
            'ownership_gate_C_pass_count': c6,
            'cluster_full_variant_consensus_count': len(cluster.get('full_variant_consensus', [])),
            'selector_research_lead': lead,
            'current_use': 'Research lead only. The lead must be checked against the video before any hard selector regression.',
            'blocks_nvt6_research': False,
            'blocks_production_promotion': not gt6_exact_locked,
        },
        {
            'case_id': 'GT_0007',
            'role': 'TIMEFRAME_GLOBAL_H1_NO_LINE_NEGATIVE_CONTROL',
            'timeframe': gt7.get('timeframe'),
            'source_interval': gt7.get('source_locator', {}),
            'soft_status': 'PASS_NEGATIVE_CONTROL' if c7 == 0 else 'FAIL_NEGATIVE_CONTROL',
            'ownership_gate_C_pass_count': c7,
            'current_use': 'Confirms that candidate existence alone must not force an H1 line; gate C currently rejects all tested bridge candidates.',
            'blocks_nvt6_research': False,
            'blocks_production_promotion': False,
        },
    ]

    hard_blocks = [x['case_id'] for x in matrix if x.get('blocks_production_promotion')]
    soft_failures = [x['case_id'] for x in matrix if str(x.get('soft_status', '')).startswith('FAIL')]

    out = {
        'schema': 'nvt6-soft-regression-matrix/0.1',
        'status': 'RESEARCH_ONLY',
        'matrix': matrix,
        'summary': {
            'soft_failure_cases': soft_failures,
            'nvt6_research_can_continue': len(soft_failures) == 0,
            'production_promotion_ready': len(hard_blocks) == 0 and len(soft_failures) == 0,
            'production_promotion_block_cases': hard_blocks,
            'hard_regression_rule': 'Only LOCKED Ground Truth with exact anchors may define hard candidate/selector acceptance.',
            'next_required_actions': [
                'Visually verify the GT_0006 unique research lead against video 00:30:50-00:31:49.',
                'Lock exact GT_0006 anchors only if visual/OHLC evidence supports them.',
                'Later quantify GT_0005 short-lived/display-suppression lifecycle thresholds.',
                'Lock GT_0001/GT_0003 exact anchors before production promotion.',
            ],
        },
        'guards': {
            'gt0005_is_not_ownership_negative': True,
            'wick_hard_delete_forbidden_from_gt0003_single_case': True,
            'gt0006_research_lead_is_not_teacher_lock': True,
            'no_production_writeback': True,
        },
        'production_writeback': False,
        'normal_run_modified': False,
        'mt4_object_writeback': False,
        'trade_authority': False,
    }

    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'status': 'PASS',
        'nvt6_research_can_continue': out['summary']['nvt6_research_can_continue'],
        'production_promotion_ready': out['summary']['production_promotion_ready'],
        'production_promotion_block_cases': hard_blocks,
        'output': str(path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
