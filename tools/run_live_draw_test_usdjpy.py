from __future__ import annotations

import argparse
import json
from pathlib import Path

from live_draw.pipeline import run_one_timeframe

TFS = ('D1', 'H4', 'H1', 'M15')


def main() -> int:
    ap = argparse.ArgumentParser(description='NCA Live Draw v1 TEST runner for USDJPY')
    ap.add_argument('--input-dir', required=True, help='Directory containing TEST_USDJPY_<TF>.csv')
    ap.add_argument('--output-dir', required=True, help='Directory for TEST state/snapshot/audit')
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    state_path = output_dir / 'TEST_USDJPY_live_state.json'
    snapshot_path = output_dir / 'TEST_USDJPY_live_snapshot.csv'
    results = {}

    for tf in TFS:
        src = input_dir / f'TEST_USDJPY_{tf}.csv'
        if not src.exists():
            results[tf] = {'status': 'NO_INPUT', 'path': str(src)}
            continue
        audit_path = output_dir / f'TEST_USDJPY_{tf}_audit.json'
        try:
            results[tf] = run_one_timeframe(
                src,
                symbol='USDJPY',
                timeframe=tf,
                state_path=state_path,
                snapshot_path=snapshot_path,
                audit_path=audit_path,
            )
        except Exception as e:
            results[tf] = {'status': 'ERROR', 'error': f'{type(e).__name__}: {e}'}

    statuses = [v.get('status') for v in results.values()]
    if all(s == 'NO_INPUT' for s in statuses):
        overall_status = 'WAITING_MARKET_INPUT'
        exit_code = 2
    elif any(s == 'ERROR' for s in statuses):
        overall_status = 'ERROR'
        exit_code = 1
    elif any(s == 'NO_INPUT' for s in statuses):
        overall_status = 'PARTIAL_INPUT'
        exit_code = 3
    else:
        overall_status = 'PASS'
        exit_code = 0

    overall = {
        'mode': 'TEST',
        'symbol': 'USDJPY',
        'overall_status': overall_status,
        'timeframes': list(TFS),
        'results': results,
        'snapshot': str(snapshot_path),
        'state': str(state_path),
        'trade_fields_emitted': False,
        'noda_engine_writeback': False,
    }
    (output_dir / 'TEST_USDJPY_run_status.json').write_text(
        json.dumps(overall, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(json.dumps(overall, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
