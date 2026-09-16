from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    ap = argparse.ArgumentParser(description='Build NVT7 research-only lifecycle event/state graph from preflight evidence.')
    ap.add_argument('--preflight', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    pre = load_json(args.preflight)
    if pre.get('schema') != 'nvt7-lifecycle-preflight/0.1':
        raise ValueError('unexpected preflight schema')
    if pre.get('all_preflight_checks_pass') is not True:
        raise ValueError('NVT7 preflight checks did not pass')

    state_specs = {
        'CURRENT_ACTIVE': {
            'candidate_valid': True,
            'visible': True,
            'stable_market_state': True,
            'role': 'CURRENT',
        },
        'REFERENCE_RETAINED': {
            'candidate_valid': True,
            'visible': True,
            'stable_market_state': True,
            'role': 'REFERENCE',
        },
        'VALID_SUPPRESSED': {
            'candidate_valid': True,
            'visible': False,
            'stable_market_state': True,
            'role': 'SUPPRESSED_VALID',
        },
        'EDIT_TRANSIENT': {
            'candidate_valid': None,
            'visible': None,
            'stable_market_state': False,
            'role': 'VIDEO_EDIT_ONLY',
        },
        'REANCHORED_CURRENT': {
            'candidate_valid': True,
            'visible': True,
            'stable_market_state': True,
            'role': 'CURRENT',
        },
    }

    edges = [
        {
            'edge_id': 'E_GT0002_UPDATE_KEEP_REFERENCE',
            'case_id': 'GT_0002',
            'event': 'UPDATE_AND_KEEP_REFERENCE',
            'from_state': 'CURRENT_ACTIVE',
            'to_states': ['REANCHORED_CURRENT', 'REFERENCE_RETAINED'],
            'market_time_transition_supported': True,
            'delete_previous_by_default': False,
            'status': 'EVIDENCE_SUPPORTED_HYPOTHESIS',
        },
        {
            'edge_id': 'E_GT0004_RESTORE_REFERENCE',
            'case_id': 'GT_0004',
            'event': 'RESTORE_PERSISTENT_REFERENCE',
            'from_state': 'NEWER_REANCHOR_OR_PC_EDIT',
            'to_states': ['REFERENCE_RETAINED'],
            'market_time_transition_supported': True,
            'delete_previous_by_default': False,
            'status': 'EVIDENCE_SUPPORTED_HYPOTHESIS',
        },
        {
            'edge_id': 'E_GT0005_SUPPRESS_VALID',
            'case_id': 'GT_0005',
            'event': 'SUPPRESS_VALID_SHORT_LIVED',
            'from_state': 'VALID_CANDIDATE',
            'to_states': ['VALID_SUPPRESSED'],
            'market_time_transition_supported': True,
            'delete_previous_by_default': False,
            'status': 'EVIDENCE_SUPPORTED_HYPOTHESIS',
        },
        {
            'edge_id': 'E_GT0006_REANCHOR_CURRENT',
            'case_id': 'GT_0006',
            'event': 'REANCHOR_CURRENT_WITHOUT_DEFAULT_DELETE',
            'from_state': 'CURRENT_ACTIVE',
            'to_states': ['REANCHORED_CURRENT'],
            'market_time_transition_supported': False,
            'delete_previous_by_default': False,
            'status': 'VIDEO_EDIT_SEQUENCE_ONLY_PENDING_MARKET_TIME_ORDER',
            'guard': 'GT_0006 proves geometry-state changes/transient edits in video, but does not by itself prove market-time transition order.',
        },
    ]

    gt6 = pre.get('case_evidence', {}).get('GT_0006', {})
    video_states = []
    for row in gt6.get('video_state_classification') or []:
        cls = row.get('class')
        if cls == 'EDIT_TRANSIENT_OR_UNRESOLVED':
            mapped = 'EDIT_TRANSIENT'
            stable = False
        elif cls in {'STABLE_GEOMETRY_CANDIDATE', 'STABLE_GEOMETRY_FAMILY'}:
            mapped = 'CURRENT_ACTIVE_OR_REANCHORED_CURRENT_CANDIDATE'
            stable = True
        else:
            mapped = 'UNRESOLVED'
            stable = False
        video_states.append({
            **row,
            'mapped_lifecycle_state': mapped,
            'stable_for_market_lifecycle_training': stable,
        })

    regression_contracts = [
        {
            'case_id': 'GT_0002',
            'must_support': ['CURRENT_ACTIVE', 'REFERENCE_RETAINED'],
            'must_not_do': ['DELETE_REFERENCE_JUST_BECAUSE_CURRENT_UPDATED'],
        },
        {
            'case_id': 'GT_0004',
            'must_support': ['REFERENCE_RETAINED'],
            'must_not_do': ['PREFER_NEWEST_REANCHOR_UNCONDITIONALLY'],
        },
        {
            'case_id': 'GT_0005',
            'must_support': ['VALID_SUPPRESSED'],
            'must_not_do': ['RECLASSIFY_SUPPRESSED_AS_INVALID_OR_NO_LINE'],
        },
        {
            'case_id': 'GT_0006',
            'must_support': ['EDIT_TRANSIENT', 'MULTIPLE_GEOMETRY_STATES'],
            'must_not_do': ['TREAT_VIDEO_EDIT_ORDER_AS_MARKET_TIME_ORDER', 'LOCK_ONE_STATIC_GEOMETRY_FROM_ALL_VIDEO_SAMPLES'],
        },
    ]

    report = {
        'schema': 'nvt7-event-state-graph/0.1',
        'status': 'RESEARCH_ONLY',
        'phase': 'NVT7-2_EVENT_STATE_GRAPH',
        'states': state_specs,
        'edges': edges,
        'gt0006_video_state_mapping': video_states,
        'sequential_regression_contracts': regression_contracts,
        'unresolved': [
            'Exact market-time sequence for GT_0006 re-anchor states.',
            'Objective threshold for GT_0005 short-lived/display suppression.',
            'Explicit RETIRED/DELETE transition evidence.',
            'Exact anchor locks for DRAFT cases where still pending.',
        ],
        'beta_freeze_ready': False,
        'next_required_action': 'Run NVT7 sequential regression before freezing lifecycle state/transition semantics.',
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
        'state_count': len(state_specs),
        'edge_count': len(edges),
        'gt0006_video_state_count': len(video_states),
        'beta_freeze_ready': False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
