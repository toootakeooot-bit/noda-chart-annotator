from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_reports(paths: list[Path]) -> list[dict]:
    reports = []
    for path in paths:
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('schema') != 'nvt-teacher-nca-diff/1.0':
            raise ValueError(f'unexpected diff schema in {path}: {data.get("schema")}')
        data['_source_path'] = str(path)
        reports.append(data)
    return reports


def ratio(num: int, den: int) -> float | None:
    return (num / den) if den else None


def main() -> int:
    ap = argparse.ArgumentParser(description='NVT3+ - aggregate decomposed validation metrics from diff reports')
    ap.add_argument('--report', action='append', default=[], help='Diff report JSON; may be repeated')
    ap.add_argument('--input-dir', help='Directory containing *.json diff reports')
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    paths = [Path(p) for p in args.report]
    if args.input_dir:
        paths.extend(sorted(Path(args.input_dir).glob('*.json')))
    # Stable unique order.
    paths = list(dict.fromkeys(paths))
    if not paths:
        raise ValueError('no diff reports supplied')

    reports = load_reports(paths)

    status_counts: dict[str, int] = {}
    failure_counts: dict[str, int] = {}
    candidate_den = candidate_ok = 0
    selector_den = selector_ok = 0
    anchor_den = anchor_ok = 0
    no_line_den = no_line_ok = 0
    scale_den = scale_ok = 0
    channel_den = channel_ok = 0

    per_case = []
    for report in reports:
        status = str(report.get('assessment_status'))
        status_counts[status] = status_counts.get(status, 0) + 1
        for f in report.get('failure_classes') or []:
            failure_counts[f] = failure_counts.get(f, 0) + 1

        scale = report.get('structure_scale_match')
        if scale is not None:
            scale_den += 1
            scale_ok += int(bool(scale))

        if report.get('expected_no_line'):
            nl = report.get('no_line_match')
            if nl is not None:
                no_line_den += 1
                no_line_ok += int(bool(nl))

        object_summaries = []
        for obj in report.get('teacher_object_results') or []:
            if obj.get('anchor_data_complete'):
                cp = obj.get('candidate_present')
                if cp is not None:
                    candidate_den += 1
                    candidate_ok += int(bool(cp))
                am = obj.get('anchor_match')
                if am not in {None, 'PENDING_GT_ANCHORS', 'OUTSIDE_TOLERANCE_OR_ABSENT'}:
                    anchor_den += 1
                    anchor_ok += 1
                elif am == 'OUTSIDE_TOLERANCE_OR_ABSENT':
                    anchor_den += 1
                sm = obj.get('selector_match')
                if cp:
                    selector_den += 1
                    selector_ok += int(bool(sm))

            ch = obj.get('channel_match')
            if ch == 'MATCH':
                channel_den += 1
                channel_ok += 1
            elif ch == 'MISMATCH':
                channel_den += 1

            object_summaries.append({
                'teacher_object_id': obj.get('teacher_object_id'),
                'candidate_present': obj.get('candidate_present'),
                'anchor_match': obj.get('anchor_match'),
                'selector_match': obj.get('selector_match'),
                'channel_match': obj.get('channel_match'),
            })

        per_case.append({
            'case_id': report.get('case_id'),
            'status': status,
            'expected_no_line': report.get('expected_no_line'),
            'no_line_match': report.get('no_line_match'),
            'failure_classes': report.get('failure_classes') or [],
            'objects': object_summaries,
            'source': report.get('_source_path'),
        })

    payload = {
        'schema': 'nvt-validation-metrics/1.0',
        'report_count': len(reports),
        'status_counts': status_counts,
        'failure_class_counts': failure_counts,
        'metrics': {
            'structure_scale_accuracy': {
                'pass': scale_ok, 'assessed': scale_den, 'rate': ratio(scale_ok, scale_den),
            },
            'candidate_recall': {
                'pass': candidate_ok, 'assessed': candidate_den, 'rate': ratio(candidate_ok, candidate_den),
            },
            'anchor_accuracy': {
                'pass': anchor_ok, 'assessed': anchor_den, 'rate': ratio(anchor_ok, anchor_den),
            },
            'selection_accuracy_given_candidate_present': {
                'pass': selector_ok, 'assessed': selector_den, 'rate': ratio(selector_ok, selector_den),
            },
            'no_line_accuracy': {
                'pass': no_line_ok, 'assessed': no_line_den, 'rate': ratio(no_line_ok, no_line_den),
            },
            'channel_accuracy': {
                'pass': channel_ok, 'assessed': channel_den, 'rate': ratio(channel_ok, channel_den),
            },
            'lifecycle_accuracy': {
                'pass': 0, 'assessed': 0, 'rate': None,
                'note': 'Sequential lifecycle scoring begins after NVT4/NVT5 event alignment.',
            },
            'role_accuracy': {
                'pass': 0, 'assessed': 0, 'rate': None,
                'note': 'Role scoring requires reviewed teacher-role ground truth.',
            },
            'render_accuracy': {
                'pass': 0, 'assessed': 0, 'rate': None,
                'note': 'Render style is intentionally downstream of structural validation.',
            },
        },
        'aggregate_score': None,
        'aggregate_score_policy': 'PROHIBITED_FOR_PROMOTION_DECISION; use decomposed metrics.',
        'cases': per_case,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'status': 'PASS',
        'report_count': len(reports),
        'status_counts': status_counts,
        'failure_class_counts': failure_counts,
        'output': str(out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
