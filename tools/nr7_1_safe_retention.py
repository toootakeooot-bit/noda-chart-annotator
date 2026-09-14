from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from run_normal import publish_validated_snapshot


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description='NR7-1 safe snapshot retention probe')
    ap.add_argument('--snapshot', required=True)
    ap.add_argument('--symbol', default='USDJPY#')
    ap.add_argument('--report', required=True)
    args = ap.parse_args()

    snapshot = Path(args.snapshot)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        'test': 'NR7-1_SAFE_SNAPSHOT_RETENTION',
        'snapshot': str(snapshot),
        'symbol': args.symbol,
        'snapshot_exists_before': snapshot.exists(),
        'expected_publish_failure_observed': False,
        'snapshot_hash_unchanged': False,
        'overall_status': 'FAIL',
    }

    if not snapshot.exists():
        report['error'] = 'VALID_SNAPSHOT_MISSING'
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    before_hash = sha256_file(snapshot)
    before_size = snapshot.stat().st_size
    report['before_sha256'] = before_hash
    report['before_size'] = before_size

    # Intentionally invalid new drawing state: the writer can create a CSV
    # header, but validation must reject it because it contains no drawing rows.
    # publish_validated_snapshot() writes only to a temporary file before PASS,
    # so the currently published valid snapshot must remain byte-identical.
    invalid_state = {'schema': 'nca-live-state/1.0', 'slots': {}}
    try:
        publish_validated_snapshot(snapshot, invalid_state, args.symbol)
        report['unexpected'] = 'INVALID_STATE_WAS_PUBLISHED'
    except Exception as exc:
        report['expected_publish_failure_observed'] = True
        report['failure_type'] = type(exc).__name__
        report['failure_message'] = str(exc)

    if snapshot.exists():
        after_hash = sha256_file(snapshot)
        after_size = snapshot.stat().st_size
        report['after_sha256'] = after_hash
        report['after_size'] = after_size
        report['snapshot_hash_unchanged'] = before_hash == after_hash and before_size == after_size
    else:
        report['after_sha256'] = None
        report['after_size'] = None

    if report['expected_publish_failure_observed'] and report['snapshot_hash_unchanged']:
        report['overall_status'] = 'PASS'

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['overall_status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
