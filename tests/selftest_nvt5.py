from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def write_csv(path: Path) -> None:
    rows = [
        ['2026-01-02 22:00:00', '100', '101', '99', '100.5', '1'],
        ['2026-01-02 23:00:00', '100.5', '102', '100', '101.5', '1'],
        ['2026-01-03 00:00:00', '101.5', '103', '101', '102.5', '1'],
        ['2026-01-03 01:00:00', '102.5', '104', '102', '103.5', '1'],
        ['2026-01-03 02:00:00', '103.5', '105', '103', '104.5', '1'],
        ['2026-01-04 00:00:00', '104.5', '106', '104', '105.5', '1'],
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['time', 'open', 'high', 'low', 'close', 'volume'])
        w.writerows(rows)


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    replay_tool = repo / 'tools' / 'nvt' / 'replay_to_time.py'
    plan_tool = repo / 'tools' / 'nvt' / 'build_nvt5_replay_plan.py'

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        input_dir = root / 'input'
        gt_dir = root / 'gt'
        out = root / 'out'
        gt_dir.mkdir(parents=True, exist_ok=True)
        out.mkdir(parents=True, exist_ok=True)

        src = input_dir / 'NVT_USDJPY#_H1.csv'
        write_csv(src)

        manifest = {
            'schema': 'nvt-market-cutoff-manifest/1.0',
            'sources': [
                {
                    'source_id': 'SELFTEST_VIDEO',
                    'expected_last_market_date': '2026-01-03',
                }
            ],
        }
        manifest_path = root / 'cutoffs.json'
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

        gt = {
            'schema': 'nvt-ground-truth/1.0',
            'case_id': 'SELFTEST_GT',
            'source_id': 'SELFTEST_VIDEO',
            'source_type': 'VIDEO',
            'symbol': 'USDJPY',
            'timeframe': 'H1',
            'decision_time': None,
            'market_data_cutoff': 'pending',
            'source_confidence': 'HIGH',
            'annotation_status': 'DRAFT',
            'source_locator': {},
            'teacher_objects': [],
            'video_events': [],
            'notes': [],
        }
        (gt_dir / 'GT_SELFTEST.json').write_text(json.dumps(gt), encoding='utf-8')

        plan_tsv = out / 'plan.tsv'
        resolved_json = out / 'resolved.json'
        plan_cmd = [
            sys.executable, str(plan_tool),
            '--ground-truth-dir', str(gt_dir),
            '--cutoff-manifest', str(manifest_path),
            '--input-dir', str(input_dir),
            '--broker-symbol', 'USDJPY#',
            '--teacher-symbol', 'USDJPY',
            '--output-tsv', str(plan_tsv),
            '--output-json', str(resolved_json),
        ]
        proc = subprocess.run(plan_cmd, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr + proc.stdout
        resolved = json.loads(resolved_json.read_text(encoding='utf-8'))
        assert resolved['status'] == 'PASS'
        assert resolved['pair_count'] == 1
        pair = resolved['pairs'][0]
        assert pair['exact_cutoff'] == '2026-01-03T02:00:00'
        assert pair['target_market_date'] == '2026-01-03'
        assert pair['frozen_bar_count'] == 5
        assert pair['excluded_future_bar_count'] == 1

        replay_out = out / 'replay'
        replay_cmd = [
            sys.executable, str(replay_tool),
            '--input-csv', str(src),
            '--symbol', 'USDJPY#',
            '--timeframe', 'H1',
            '--cutoff', pair['exact_cutoff'],
            '--case-id', 'SELFTEST_NVT5',
            '--output-dir', str(replay_out),
        ]
        proc = subprocess.run(replay_cmd, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr + proc.stdout
        replay_manifest = json.loads(
            (replay_out / 'SELFTEST_NVT5_USDJPY#_H1_replay.json').read_text(encoding='utf-8')
        )
        assert replay_manifest['look_ahead_guard'] == 'PASS'
        assert replay_manifest['frozen_bar_count'] == 5
        assert replay_manifest['excluded_future_bar_count'] == 1
        assert replay_manifest['effective_last_closed_bar'] == '2026-01-03T02:00:00'
        assert replay_manifest['production_writeback'] is False
        assert replay_manifest['snapshot_writeback'] is False
        assert replay_manifest['mt4_object_writeback'] is False
        assert replay_manifest['trade_authority'] is False

    print('NVT5 SELFTEST PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
