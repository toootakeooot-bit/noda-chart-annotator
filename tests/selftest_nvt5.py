from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def write_csv(path: Path) -> None:
    rows = [
        ['2026-01-01 00:00:00', '100', '101', '99', '100.5', '1'],
        ['2026-01-02 00:00:00', '100.5', '102', '100', '101.5', '1'],
        ['2026-01-03 00:00:00', '101.5', '103', '101', '102.5', '1'],
        ['2026-01-04 00:00:00', '102.5', '104', '102', '103.5', '1'],
        ['2026-01-05 00:00:00', '103.5', '105', '103', '104.5', '1'],
    ]
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['time', 'open', 'high', 'low', 'close', 'volume'])
        w.writerows(rows)


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    tool = repo / 'tools' / 'nvt' / 'replay_to_time.py'
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        src = root / 'source.csv'
        out = root / 'out'
        write_csv(src)
        cmd = [
            sys.executable, str(tool),
            '--input-csv', str(src),
            '--symbol', 'USDJPY#',
            '--timeframe', 'D1',
            '--cutoff', '2026-01-03T23:59:59',
            '--case-id', 'SELFTEST_NVT5',
            '--output-dir', str(out),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr + proc.stdout
        manifest = json.loads((out / 'SELFTEST_NVT5_USDJPY#_D1_replay.json').read_text(encoding='utf-8'))
        assert manifest['look_ahead_guard'] == 'PASS'
        assert manifest['frozen_bar_count'] == 3
        assert manifest['excluded_future_bar_count'] == 2
        assert manifest['effective_last_closed_bar'] == '2026-01-03T00:00:00'
        assert manifest['production_writeback'] is False
        assert manifest['mt4_object_writeback'] is False
    print('NVT5 SELFTEST PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
