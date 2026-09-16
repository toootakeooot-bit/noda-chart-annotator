from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def note_map(gt: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in gt.get('notes') or []:
        if not isinstance(raw, str) or '=' not in raw:
            continue
        key, value = raw.split('=', 1)
        out[key.strip()] = value.strip()
    return out


def find_event(gt: dict, action: str | None = None) -> dict | None:
    for event in gt.get('video_events') or []:
        if action is None or event.get('action') == action:
            return event
    return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description='NVT7 research-only lifecycle preflight from GT_0002/4/5 and GT_0006 visual state sequence.'
    )
    ap.add_argument('--gt0002', required=True)
    ap.add_argument('--gt0004', required=True)
    ap.add_argument('--gt0005', required=True)
    ap.add_argument('--gt0006-sequence', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    gt2 = load_json(args.gt0002)
    gt4 = load_json(args.gt0004)
    gt5 = load_json(args.gt0005)
    gt6 = load_json(args.gt0006_sequence)

    if gt2.get('case_id') != 'GT_0002':
        raise ValueError('GT_0002 input mismatch')
    if gt4.get('case_id') != 'GT_0004':
        raise ValueError('GT_0004 input mismatch')
    if gt5.get('case_id') != 'GT_0005':
        raise ValueError('GT_0005 input mismatch')
    if gt6.get('case_id') != 'GT_0006':
        raise ValueError('GT_0006 sequence input mismatch')

    gt2_roles = {str(o.get('teacher_role')) for o in gt2.get('teacher_objects') or []}
    gt2_actions = {str(o.get('action')) for o in gt2.get('teacher_objects') or []}
    gt2_event = find_event(gt2, 'MOVE')

    gt4_event = find_event(gt4, 'REPLACE')
    gt4_notes = ' '.join(
        str(n) for obj in gt4.get('teacher_objects') or [] for n in (obj.get('notes') or [])
    ).lower()

    gt5_notes = note_map(gt5)
    gt5_event = find_event(gt5)

    observations = {str(o.get('id')): o for o in gt6.get('observation_results') or []}
    fixed = gt6.get('single_fixed_geometry_test') or {}
    findings = gt6.get('research_findings') or {}

    v1 = observations.get('V1_GENTLE_FAMILY') or {}
    v2 = observations.get('V2_TRANSIENT_OR_DIFFERENT_GEOMETRY') or {}
    v3 = observations.get('V3_STEEPER_STATE') or {}
    v4 = observations.get('V4_LATER_HIGH_REANCHOR_STATE') or {}

    checks = {
        'gt0002_has_current_and_reference_roles': {'CURRENT', 'REFERENCE'}.issubset(gt2_roles),
        'gt0002_has_keep_and_move_actions': {'KEEP', 'MOVE'}.issubset(gt2_actions),
        'gt0002_move_event_present': gt2_event is not None,
        'gt0004_replace_event_present': gt4_event is not None,
        'gt0004_persistent_original_reference_evidence': (
            'kept continuously' in gt4_notes or 'persistent original line' in gt4_notes or 'original position' in gt4_notes
        ),
        'gt0005_candidate_valid': gt5_notes.get('candidate_valid', '').lower() == 'true',
        'gt0005_display_suppressed': gt5_notes.get('display_policy') == 'SUPPRESS_TO_AVOID_LINE_CLUTTER',
        'gt0005_not_ownership_rejection': gt5_notes.get('ownership_rejection', '').lower() == 'false',
        'gt0006_same_object_name_across_sequence': findings.get('same_mt4_object_name_observed_across_sequence') is True,
        'gt0006_no_single_fixed_geometry_fits_all_samples': fixed.get('candidate_count_fitting_all_samples') == 0,
        'gt0006_v1_has_stable_family': int(v1.get('within_tolerance_count') or 0) >= 1,
        'gt0006_v2_has_no_fixed_candidate_match': int(v2.get('within_tolerance_count') or 0) == 0,
        'gt0006_v3_has_unique_match': int(v3.get('within_tolerance_count') or 0) == 1,
        'gt0006_v4_has_unique_match': int(v4.get('within_tolerance_count') or 0) == 1,
    }

    lifecycle_state_hypotheses = [
        {
            'state': 'CURRENT_ACTIVE',
            'meaning': 'Currently active geometry used for monitoring/drawing.',
            'evidence_cases': ['GT_0002', 'GT_0006'],
            'status': 'HYPOTHESIS',
        },
        {
            'state': 'REFERENCE_RETAINED',
            'meaning': 'Older still-useful structure retained alongside a newer current structure.',
            'evidence_cases': ['GT_0002', 'GT_0004'],
            'status': 'HYPOTHESIS',
        },
        {
            'state': 'VALID_SUPPRESSED',
            'meaning': 'Structurally valid line intentionally not displayed because of short life / clutter cost.',
            'evidence_cases': ['GT_0005'],
            'status': 'HYPOTHESIS',
        },
        {
            'state': 'EDIT_TRANSIENT',
            'meaning': 'Video-edit/drag sample that must not be treated as a stable market-time lifecycle state.',
            'evidence_cases': ['GT_0006'],
            'status': 'HYPOTHESIS',
        },
        {
            'state': 'REANCHORED_CURRENT',
            'meaning': 'Current line geometry after a supported anchor update; does not imply old reference deletion.',
            'evidence_cases': ['GT_0002', 'GT_0006'],
            'status': 'HYPOTHESIS',
        },
    ]

    case_evidence = {
        'GT_0002': {
            'role': 'UPDATE_CURRENT_WHILE_KEEPING_REFERENCE',
            'teacher_roles': sorted(gt2_roles),
            'teacher_actions': sorted(gt2_actions),
            'event_action': None if gt2_event is None else gt2_event.get('action'),
            'lifecycle_inference': 'A newer current channel may coexist with an older useful reference channel.',
            'guard': 'Do not collapse this into newest-only replacement.',
        },
        'GT_0004': {
            'role': 'PERSISTENT_REFERENCE_BEATS_NEWER_REANCHOR_FOR_MONITORING',
            'event_action': None if gt4_event is None else gt4_event.get('action'),
            'lifecycle_inference': 'Monitoring continuity can justify restoring/keeping the original reference instead of a newer re-anchor.',
            'guard': 'Newest geometrically valid candidate is not automatically the preferred monitoring reference.',
        },
        'GT_0005': {
            'role': 'VALID_BUT_DISPLAY_SUPPRESSED',
            'event_action': None if gt5_event is None else gt5_event.get('action'),
            'candidate_valid': gt5_notes.get('candidate_valid'),
            'display_policy': gt5_notes.get('display_policy'),
            'lifecycle_character': gt5_notes.get('lifecycle_character'),
            'lifecycle_inference': 'Validity and visibility must be separate dimensions.',
            'guard': 'Suppressed does not mean invalid, deleted, or ownership-rejected.',
        },
        'GT_0006': {
            'role': 'SELECTOR_TO_LIFECYCLE_BRIDGE',
            'same_object_name': gt6.get('source', {}).get('mt4_object_name'),
            'fixed_geometry_fit_count': fixed.get('candidate_count_fitting_all_samples'),
            'video_state_classification': [
                {
                    'observation_id': 'V1_GENTLE_FAMILY',
                    'class': 'STABLE_GEOMETRY_FAMILY',
                    'within_tolerance_count': v1.get('within_tolerance_count'),
                },
                {
                    'observation_id': 'V2_TRANSIENT_OR_DIFFERENT_GEOMETRY',
                    'class': 'EDIT_TRANSIENT_OR_UNRESOLVED',
                    'within_tolerance_count': v2.get('within_tolerance_count'),
                },
                {
                    'observation_id': 'V3_STEEPER_STATE',
                    'class': 'STABLE_GEOMETRY_CANDIDATE',
                    'within_tolerance_count': v3.get('within_tolerance_count'),
                    'best_anchor2_time': (v3.get('best_match') or {}).get('anchor2_time'),
                },
                {
                    'observation_id': 'V4_LATER_HIGH_REANCHOR_STATE',
                    'class': 'STABLE_GEOMETRY_CANDIDATE',
                    'within_tolerance_count': v4.get('within_tolerance_count'),
                    'best_anchor2_time': (v4.get('best_match') or {}).get('anchor2_time'),
                },
            ],
            'lifecycle_inference': 'Same MT4 object name can be observed with multiple geometry states; selector and lifecycle responsibilities must be separated.',
            'guard': 'Video edit order is not automatically market-time lifecycle order.',
        },
    }

    transition_hypotheses = [
        {
            'name': 'UPDATE_AND_KEEP_REFERENCE',
            'from': ['CURRENT_ACTIVE'],
            'to': ['REANCHORED_CURRENT', 'REFERENCE_RETAINED'],
            'evidence_cases': ['GT_0002'],
            'hard_rule': False,
        },
        {
            'name': 'RESTORE_PERSISTENT_REFERENCE',
            'from': ['NEWER_REANCHOR_OR_PC_EDIT'],
            'to': ['REFERENCE_RETAINED'],
            'evidence_cases': ['GT_0004'],
            'hard_rule': False,
        },
        {
            'name': 'SUPPRESS_VALID_SHORT_LIVED',
            'from': ['VALID_CANDIDATE'],
            'to': ['VALID_SUPPRESSED'],
            'evidence_cases': ['GT_0005'],
            'hard_rule': False,
        },
        {
            'name': 'REANCHOR_CURRENT_WITHOUT_DEFAULT_DELETE',
            'from': ['CURRENT_ACTIVE'],
            'to': ['REANCHORED_CURRENT'],
            'evidence_cases': ['GT_0006', 'GT_0002'],
            'hard_rule': False,
            'guard': 'Do not infer deletion of the previous useful structure without explicit evidence.',
        },
    ]

    all_checks_pass = all(checks.values())
    report = {
        'schema': 'nvt7-lifecycle-preflight/0.1',
        'status': 'RESEARCH_ONLY',
        'phase': 'NVT7-1_PRELIMINARY_LIFECYCLE_EVIDENCE',
        'checks': checks,
        'all_preflight_checks_pass': all_checks_pass,
        'case_evidence': case_evidence,
        'state_hypotheses': lifecycle_state_hypotheses,
        'transition_hypotheses': transition_hypotheses,
        'model_guards': {
            'latest_is_not_automatically_best': True,
            'validity_and_visibility_are_separate': True,
            'same_object_name_does_not_mean_same_geometry': True,
            'video_edit_order_is_not_market_time_order': True,
            'transient_edit_must_not_become_stable_state': True,
            'old_reference_is_not_deleted_by_default': True,
            'retired_delete_transition_not_fixed_yet': True,
        },
        'next_required_actions': [
            'Build a research-only event/state graph using these hypotheses.',
            'Separate stable post-edit geometry from transient drag samples in GT_0006.',
            'Run sequential regression against GT_0002 / GT_0004 / GT_0005 / GT_0006.',
            'Only after the sequential regression, decide whether lifecycle state names/transition rules should be fixed for NVT7 beta.',
        ],
        'nvt7_research_can_continue': all_checks_pass,
        'production_promotion_ready': False,
        'production_writeback': False,
        'normal_run_modified': False,
        'mt4_object_writeback': False,
        'trade_authority': False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'status': 'PASS' if all_checks_pass else 'REVIEW_REQUIRED',
        'output': str(out),
        'all_preflight_checks_pass': all_checks_pass,
        'nvt7_research_can_continue': all_checks_pass,
        'state_hypothesis_count': len(lifecycle_state_hypotheses),
        'transition_hypothesis_count': len(transition_hypotheses),
    }, ensure_ascii=False, indent=2))
    return 0 if all_checks_pass else 2


if __name__ == '__main__':
    raise SystemExit(main())
