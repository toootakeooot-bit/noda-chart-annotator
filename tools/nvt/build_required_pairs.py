from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser(description='Build Ground-Truth-required source/timeframe pairs for NVT2.')
    ap.add_argument('--ground-truth-dir', required=True)
    ap.add_argument('--cutoff-manifest', required=True)
    ap.add_argument('--symbol', default='USDJPY')
    ap.add_argument('--output-tsv', required=True)
    args = ap.parse_args()

    gt_dir = Path(args.ground_truth_dir)
    manifest = load_json(Path(args.cutoff_manifest))

    cutoff_by_source = {
        str(src['source_id']): f"{src['expected_last_market_date']}T23:59:59"
        for src in manifest.get('sources', [])
    }

    pair_map: dict[tuple[str, str], dict] = {}
    for path in sorted(gt_dir.glob('GT_*.json')):
        if path.name == 'GT_TEMPLATE.json':
            continue
        gt = load_json(path)
        if str(gt.get('symbol')) != args.symbol:
            continue
        source_id = str(gt.get('source_id') or '')
        timeframe = str(gt.get('timeframe') or '')
        case_id = str(gt.get('case_id') or path.stem)
        if not source_id or not timeframe:
            raise ValueError(f'missing source_id/timeframe in {path}')
        if source_id not in cutoff_by_source:
            raise ValueError(f'no cutoff manifest entry for {source_id}')
        key = (source_id, timeframe)
        row = pair_map.setdefault(key, {
            'source_id': source_id,
            'timeframe': timeframe,
            'cutoff': cutoff_by_source[source_id],
            'cases': [],
        })
        row['cases'].append(case_id)

    rows = [pair_map[k] for k in sorted(pair_map)]
    if not rows:
        raise ValueError(f'no {args.symbol} Ground Truth source/timeframe pairs found')

    out = Path(args.output_tsv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='ascii', newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['source_id', 'timeframe', 'cutoff', 'cases'],
            delimiter='\t',
            lineterminator='\n',
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                'source_id': row['source_id'],
                'timeframe': row['timeframe'],
                'cutoff': row['cutoff'],
                'cases': ','.join(row['cases']),
            })

    print(json.dumps({
        'status': 'PASS',
        'output': str(out),
        'required_pairs': len(rows),
        'required_timeframes': sorted({r['timeframe'] for r in rows}),
        'cases': sum(len(r['cases']) for r in rows),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
