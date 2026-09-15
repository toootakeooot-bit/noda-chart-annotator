from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    ap = argparse.ArgumentParser(description='Bundle NVT5 cutoffs/replay summary/anchor workbenches for external audit review.')
    ap.add_argument('--output-root', required=True, help='noda_draw/nvt_output directory')
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    root = Path(args.output_root)
    resolved_path = root / 'NVT5_RESOLVED_CUTOFFS.json'
    summary_path = root / 'NVT5_USDJPY_REPLAY_SUMMARY.json'
    replay_root = root / 'nvt5_replay'

    missing = [str(p) for p in (resolved_path, summary_path, replay_root) if not p.exists()]
    if missing:
        raise FileNotFoundError('missing NVT5 output(s): ' + '; '.join(missing))

    resolved = load_json(resolved_path)
    summary = load_json(summary_path)

    workbench_paths = sorted(replay_root.glob('**/workbench_GT_*.json'))
    replay_manifest_paths = sorted(replay_root.glob('**/*_replay.json'))
    if not workbench_paths:
        raise ValueError('no workbench_GT_*.json files found')

    workbenches = [load_json(p) for p in workbench_paths]
    replay_manifests = [load_json(p) for p in replay_manifest_paths]

    case_ids = sorted(str(w.get('case_id')) for w in workbenches)
    expected_cases = [f'GT_{i:04d}' for i in range(1, 8)]
    missing_cases = [c for c in expected_cases if c not in case_ids]
    duplicate_cases = sorted({c for c in case_ids if case_ids.count(c) > 1})

    replay_checks = []
    for r in replay_manifests:
        replay_checks.append({
            'case_id': r.get('case_id'),
            'timeframe': r.get('timeframe'),
            'requested_cutoff': r.get('requested_cutoff'),
            'effective_last_closed_bar': r.get('effective_last_closed_bar'),
            'frozen_bar_count': r.get('frozen_bar_count'),
            'excluded_future_bar_count': r.get('excluded_future_bar_count'),
            'look_ahead_guard': r.get('look_ahead_guard'),
            'source_sha256': r.get('source_sha256'),
            'frozen_sha256': r.get('frozen_sha256'),
        })

    guard_failures = [
        x for x in replay_checks
        if x.get('look_ahead_guard') != 'PASS'
    ]

    payload = {
        'schema': 'nvt5-review-bundle/1.0',
        'status': 'PASS' if not missing_cases and not duplicate_cases and not guard_failures else 'FAIL',
        'purpose': 'portable audit/review bundle; no production writeback',
        'resolved_cutoffs': resolved,
        'replay_summary': summary,
        'replay_checks': replay_checks,
        'workbenches': workbenches,
        'audit': {
            'workbench_count': len(workbenches),
            'workbench_case_ids': case_ids,
            'missing_expected_cases': missing_cases,
            'duplicate_cases': duplicate_cases,
            'replay_manifest_count': len(replay_checks),
            'look_ahead_guard_failures': guard_failures,
        },
        'safety': {
            'production_writeback': False,
            'snapshot_writeback': False,
            'mt4_object_writeback': False,
            'trade_authority': False,
        },
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'status': payload['status'],
        'output': str(out),
        'workbench_count': len(workbenches),
        'cases': case_ids,
        'replay_manifest_count': len(replay_checks),
        'look_ahead_guard_failures': len(guard_failures),
    }, ensure_ascii=True, indent=2))
    return 0 if payload['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
