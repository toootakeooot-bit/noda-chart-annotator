from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    forbidden = ('entry_price', 'stop_loss', 'take_profit', 'risk_reward', 'order_type', 'ticket')
    scan = []
    for p in list((ROOT/'tools'/'live_draw').glob('*.py')) + list((ROOT/'mt4').glob('*.mq4')):
        text = p.read_text(encoding='utf-8').lower()
        hits = [x for x in forbidden if x in text]
        scan.append({'file': str(p.relative_to(ROOT)), 'forbidden_hits': hits})
        if hits:
            print(json.dumps({'status':'FAIL','reason':'FORBIDDEN_FIELD','scan':scan}, indent=2))
            return 2

    cp = subprocess.run([sys.executable, str(ROOT/'tests'/'selftest_live_draw.py')], capture_output=True, text=True)
    result = {
        'status': 'PASS' if cp.returncode == 0 else 'FAIL',
        'static_forbidden_scan': scan,
        'selftest_returncode': cp.returncode,
        'selftest_stdout': cp.stdout,
        'selftest_stderr': cp.stderr,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if cp.returncode == 0 else cp.returncode


if __name__ == '__main__':
    raise SystemExit(main())
