from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Verify GT_0005 semantics before GT_0006 ownership/selector research.'
    )
    ap.add_argument('--ground-truth', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    gt = load_json(args.ground_truth)
    if gt.get('case_id') != 'GT_0005':
        raise ValueError(f"expected GT_0005, got {gt.get('case_id')}")

    notes = {str(x).strip() for x in gt.get('notes', [])}
    required_exact = {
        'teacher_term=TURN_LINE',
        'structure_class=SMALL_DOW_TL',
        'candidate_valid=true',
        'can_draw_from_valid_highs=true',
        'can_draw_during_full_small_dow_phase=true',
        'geometry_character=STEEP_ANGLE',
        'lifecycle_character=SHORT_LIVED_BECOMES_UNNECESSARY_WITH_TIME',
        'displayed_in_reference=false',
        'ownership_rejection=false',
        'invalid_line=false',
        'process_order=EVALUATE_DISPLAY_SUPPRESSION_BEFORE_GT_0006_SELECTOR',
    }
    missing = sorted(required_exact - notes)
    suppress_note = next((x for x in notes if x.startswith('display_policy=SUPPRESS')), None)
    exact_anchor_pending = 'exact_anchor_target=pending' in notes

    pass_semantics = not missing and suppress_note is not None
    report = {
        'schema': 'nvt6-gt0005-display-suppression-precheck/0.1',
        'status': 'PASS' if pass_semantics else 'FAIL',
        'mode': 'RESEARCH_ONLY',
        'case_id': 'GT_0005',
        'source_locator': gt.get('source_locator'),
        'semantic_classification': {
            'candidate_valid': 'candidate_valid=true' in notes,
            'turn_line': 'teacher_term=TURN_LINE' in notes,
            'small_dow_tl': 'structure_class=SMALL_DOW_TL' in notes,
            'steep_angle': 'geometry_character=STEEP_ANGLE' in notes,
            'short_lived': (
                'lifecycle_character=SHORT_LIVED_BECOMES_UNNECESSARY_WITH_TIME' in notes
            ),
            'display_suppressed': suppress_note is not None,
            'display_suppression_reason': suppress_note,
            'ownership_negative': False,
            'invalid_line': False,
            'exact_anchor_pending': exact_anchor_pending,
        },
        'process_guard': {
            'must_be_processed_before_gt0006_selector': True,
            'must_not_be_used_as_ownership_negative': True,
            'must_not_be_used_as_invalid_candidate_negative': True,
            'exact_anchor_not_required_to_continue_gt0006_research': True,
            'exact_anchor_required_later_for_lifecycle_visibility_quantification': True,
        },
        'missing_required_semantics': missing,
        'interpretation': (
            'GT_0005 is a valid small-Dow turn line that may be drawn from valid highs, '
            'including during a full small-Dow phase. Its steep angle makes it short-lived, '
            'and it is intentionally not displayed to avoid line clutter. This is a visibility/'
            'lifecycle suppression case, not an ownership rejection.'
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
        'status': report['status'],
        'case_id': 'GT_0005',
        'display_suppressed': report['semantic_classification']['display_suppressed'],
        'ownership_negative': False,
        'exact_anchor_pending': exact_anchor_pending,
        'output': str(out),
    }, ensure_ascii=False, indent=2))
    return 0 if pass_semantics else 2


if __name__ == '__main__':
    raise SystemExit(main())
