from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description='Build ASCII case index for NVT3 PowerShell runner.')
    ap.add_argument('--ground-truth-dir', required=True)
    ap.add_argument('--symbol', default='USDJPY')
    ap.add_argument('--output-tsv', required=True)
    args = ap.parse_args()

    gt_dir = Path(args.ground_truth_dir)
    rows = []
    for path in sorted(gt_dir.glob('GT_*.json')):
        if path.name == 'GT_TEMPLATE.json':
            continue
        with path.open('r', encoding='utf-8') as f:
            gt = json.load(f)
        if str(gt.get('symbol')) != args.symbol:
            continue
        rows.append({
            'case_id': str(gt.get('case_id') or path.stem),
            'source_id': str(gt.get('source_id') or ''),
            'timeframe': str(gt.get('timeframe') or ''),
            'ground_truth_path': str(path.resolve()),
        })

    if not rows:
        raise ValueError(f'no {args.symbol} Ground Truth cases found')

    out = Path(args.output_tsv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='ascii', newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['case_id', 'source_id', 'timeframe', 'ground_truth_path'],
            delimiter='\t',
            lineterminator='\n',
        )
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({
        'status': 'PASS',
        'output': str(out),
        'cases': len(rows),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
