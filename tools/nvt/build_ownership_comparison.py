from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def slim_case(payload: dict) -> dict:
    ev = payload.get('candidate_evidence', {})
    exp = payload.get('teacher_expectation', {})
    top = ev.get('latest_origin_bridge_gentlest_top10', [])
    return {
        'case_id': payload.get('case_id'),
        'timeframe': payload.get('timeframe'),
        'observation': payload.get('observation'),
        'expected_no_line': exp.get('expected_no_line'),
        'no_line_scope': exp.get('no_line_scope'),
        'display_suppressed_valid_line': exp.get('display_suppressed_valid_line'),
        'ownership_rejection': exp.get('ownership_rejection'),
        'teacher_line_expected': exp.get('teacher_line_expected'),
        'teacher_direction': exp.get('teacher_direction'),
        'directional_candidate_count': ev.get('directional_candidate_count', 0),
        'provenance_counts': ev.get('provenance_counts', {}),
        'latest_origin_bridge_count': ev.get('latest_origin_bridge_count', 0),
        'latest_origin_bridge_gentlest_top5': top[:5],
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Compare NVT6 ownership evidence across GT_0005/GT_0006/GT_0007.'
    )
    ap.add_argument('--ownership-dir', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    root = Path(args.ownership_dir)
    required = ['GT_0005', 'GT_0006', 'GT_0007']
    loaded = {}
    for case_id in required:
        path = root / f'{case_id}_STRUCTURE_OWNERSHIP_EVIDENCE.json'
        if not path.exists():
            raise FileNotFoundError(f'missing ownership evidence: {path}')
        loaded[case_id] = load_json(path)

    cases = {cid: slim_case(loaded[cid]) for cid in required}
    c5 = cases['GT_0005']
    c6 = cases['GT_0006']
    c7 = cases['GT_0007']

    c7_prov = c7.get('provenance_counts', {})
    c6_prov = c6.get('provenance_counts', {})

    guards = {
        'gt0005_is_valid_display_suppression_control': bool(
            c5.get('display_suppressed_valid_line') is True
            and c5.get('ownership_rejection') is False
            and c5.get('expected_no_line') is False
        ),
        'gt0005_must_not_be_used_as_ownership_negative': bool(
            c5.get('display_suppressed_valid_line') is True
            and c5.get('ownership_rejection') is False
        ),
        'candidate_presence_cannot_define_ownership': bool(
            c7.get('no_line_scope') == 'TIMEFRAME_GLOBAL'
            and c7.get('directional_candidate_count', 0) > 0
        ),
        'p38_micro_presence_cannot_define_ownership': bool(
            c7.get('no_line_scope') == 'TIMEFRAME_GLOBAL'
            and c7_prov.get('P38_MICRO', 0) > 0
        ),
        'latest_origin_bridge_presence_cannot_define_ownership': bool(
            c7.get('no_line_scope') == 'TIMEFRAME_GLOBAL'
            and c7.get('latest_origin_bridge_count', 0) > 0
        ),
        'gt0006_positive_recall_present': bool(
            c6.get('teacher_line_expected')
            and (
                c6_prov.get('P38_MICRO', 0) > 0
                or c6.get('latest_origin_bridge_count', 0) > 0
            )
        ),
    }

    report = {
        'schema': 'nvt-ownership-comparison/0.2',
        'status': 'RESEARCH_ONLY',
        'case_order': ['GT_0005', 'GT_0006', 'GT_0007'],
        'cases': cases,
        'guards': guards,
        'conclusion': {
            'ownership_rule_status': 'NOT_YET_IDENTIFIED',
            'selector_gate_required': True,
            'candidate_presence_is_not_sufficient': guards[
                'candidate_presence_cannot_define_ownership'
            ],
            'provenance_alone_is_not_sufficient': bool(
                guards['p38_micro_presence_cannot_define_ownership']
                or guards['latest_origin_bridge_presence_cannot_define_ownership']
            ),
            'gt0005_role': (
                'VALID_SMALL_DOW_TURN_LINE_DISPLAY_SUPPRESSION_CONTROL; process before GT_0006, '
                'but do not use as ownership-negative training evidence.'
            ),
            'reason': (
                'GT_0005 is a valid small-Dow turn line that is intentionally omitted from the '
                'display because steep turn lines become unnecessary quickly and displaying all '
                'of them would create clutter. GT_0007, not GT_0005, remains the timeframe-global '
                'H1 NO-LINE ownership negative control.'
            ),
            'next_feature_families_to_probe': [
                'relationship_to_higher_timeframe_structure',
                'origin_recency_and_structural_role',
                'cluster_edge_position',
                'wick_outlier_strength',
                'candidate_age_and_elapsed_hours',
                'slope_relative_to_peer_cluster',
                'gt0005_exact_anchor_for_lifecycle_and_visibility_policy_scoring',
            ],
        },
        'interpretation_guard': (
            'This comparison does not produce a production ownership rule and must not be used '
            'to suppress or draw MT4 objects. GT_0005 display suppression is a separate visibility '
            '/ lifecycle concern from ownership validity.'
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
        'guards': guards,
        'ownership_rule_status': report['conclusion']['ownership_rule_status'],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
