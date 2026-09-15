from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_TOP_LEVEL = (
    'schema',
    'case_id',
    'source_id',
    'source_type',
    'symbol',
    'timeframe',
    'market_data_cutoff',
    'source_confidence',
    'annotation_status',
)


def validate_case(path: Path) -> tuple[dict | None, list[str]]:
    errors: list[str] = []
    try:
        with path.open('r', encoding='utf-8') as f:
            payload = json.load(f)
    except json.JSONDecodeError as exc:
        return None, [
            f'{path}: JSON_SYNTAX line={exc.lineno} column={exc.colno} char={exc.pos}: {exc.msg}'
        ]
    except UnicodeDecodeError as exc:
        return None, [f'{path}: UTF8_DECODE_ERROR: {exc}']

    if not isinstance(payload, dict):
        return payload, [f'{path}: top-level JSON must be an object']

    for key in REQUIRED_TOP_LEVEL:
        if key not in payload:
            errors.append(f'{path}: missing required field {key}')

    if not isinstance(payload.get('teacher_objects', []), list):
        errors.append(f'{path}: teacher_objects must be an array')
    if not isinstance(payload.get('video_events', []), list):
        errors.append(f'{path}: video_events must be an array')
    if 'notes' in payload and not isinstance(payload['notes'], list):
        errors.append(f'{path}: notes must be an array under schema v1')

    return payload, errors


def main() -> int:
    ap = argparse.ArgumentParser(description='Validate all NVT Ground Truth JSON before NVT2/NVT3.')
    ap.add_argument('--ground-truth-dir', required=True)
    args = ap.parse_args()

    gt_dir = Path(args.ground_truth_dir)
    files = [p for p in sorted(gt_dir.glob('GT_*.json')) if p.name != 'GT_TEMPLATE.json']
    if not files:
        print('NVT GROUND TRUTH VALIDATION FAIL: no GT_*.json cases found')
        return 2

    all_errors: list[str] = []
    case_ids: list[str] = []
    for path in files:
        payload, errors = validate_case(path)
        all_errors.extend(errors)
        if isinstance(payload, dict):
            case_ids.append(str(payload.get('case_id') or path.stem))

    if all_errors:
        print('NVT GROUND TRUTH VALIDATION FAIL')
        for err in all_errors:
            print(f'  {err}')
        return 1

    print(json.dumps({
        'status': 'PASS',
        'validated_cases': len(files),
        'case_ids': case_ids,
    }, ensure_ascii=True, indent=2))
    print('NVT GROUND TRUTH VALIDATION PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
