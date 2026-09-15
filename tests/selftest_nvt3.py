from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from nvt.compare_teacher import compare_case  # noqa: E402


def candidate_dump(selected: bool = True) -> dict:
    cid = 'RISING:2026-01-01T00:00:00:2026-01-03T00:00:00'
    return {
        'schema': 'nvt-candidate-dump/1.0',
        'symbol': 'USDJPY',
        'timeframe': 'D1',
        'effective_last_closed_bar': '2026-01-10T00:00:00',
        'selected_large_candidate_id': cid if selected else None,
        'selected_mid_candidate_id': None,
        'candidates': [{
            'candidate_id': cid,
            'direction': 'RISING',
            'anchor1': {'time': '2026-01-01T00:00:00', 'bar_index': 10},
            'anchor2': {'time': '2026-01-03T00:00:00', 'bar_index': 12},
            'ch_anchor': {'time': '2026-01-02T00:00:00', 'bar_index': 11},
            'selected_as_large': selected,
            'selected_as_mid': False,
        }],
    }


def gt_with_anchors() -> dict:
    return {
        'schema': 'nvt-ground-truth/1.0',
        'case_id': 'SELFTEST_EXACT',
        'symbol': 'USDJPY',
        'timeframe': 'D1',
        'annotation_status': 'REVIEWED',
        'teacher_objects': [{
            'object_id': 'TEACHER_TL',
            'object_type': 'TL',
            'direction': 'UP',
            'teacher_role': 'CURRENT',
            'anchor1_time': '2026-01-01T00:00:00',
            'anchor2_time': '2026-01-03T00:00:00',
        }],
    }


def main() -> int:
    exact = compare_case(gt_with_anchors(), candidate_dump(selected=True), 1)
    assert exact['assessment_status'] == 'PASS', exact
    obj = exact['teacher_object_results'][0]
    assert obj['candidate_present'] is True
    assert obj['anchor_match'] == 'EXACT_BAR'
    assert obj['selector_match'] is True

    unselected = compare_case(gt_with_anchors(), candidate_dump(selected=False), 1)
    assert unselected['assessment_status'] == 'FAIL', unselected
    assert 'SELECTION' in unselected['failure_classes']

    missing_dump = candidate_dump(selected=False)
    missing_dump['candidates'] = []
    missing = compare_case(gt_with_anchors(), missing_dump, 1)
    assert missing['assessment_status'] == 'FAIL', missing
    assert 'CANDIDATE_ABSENT' in missing['failure_classes']

    pending_gt = gt_with_anchors()
    pending_gt['case_id'] = 'SELFTEST_PENDING'
    pending_gt['teacher_objects'][0]['anchor1_time'] = 'UNKNOWN'
    pending = compare_case(pending_gt, candidate_dump(selected=True), 1)
    assert pending['assessment_status'] == 'PENDING_GROUND_TRUTH', pending
    assert 'GROUND_TRUTH_ANCHORS_PENDING' in pending['failure_classes']

    no_line_gt = {
        'schema': 'nvt-ground-truth/1.0',
        'case_id': 'SELFTEST_NO_LINE',
        'symbol': 'USDJPY',
        'timeframe': 'D1',
        'annotation_status': 'REVIEWED',
        'teacher_objects': [],
    }
    no_line_fail = compare_case(no_line_gt, candidate_dump(selected=True), 1)
    assert no_line_fail['assessment_status'] == 'FAIL'
    assert no_line_fail['no_line_match'] is False
    assert 'NO_LINE_MISMATCH' in no_line_fail['failure_classes']

    no_line_dump = candidate_dump(selected=False)
    no_line_dump['selected_large_candidate_id'] = None
    no_line_dump['selected_mid_candidate_id'] = None
    for c in no_line_dump['candidates']:
        c['selected_as_large'] = False
        c['selected_as_mid'] = False
    no_line_pass = compare_case(no_line_gt, no_line_dump, 1)
    assert no_line_pass['assessment_status'] == 'PASS'
    assert no_line_pass['no_line_match'] is True

    print('NVT3 SELFTEST PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
