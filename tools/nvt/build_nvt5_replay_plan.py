from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from live_draw.market_input import load_ohlc_csv  # noqa: E402


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def safe_file_symbol(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', '_', value.strip())


def main() -> int:
    ap = argparse.ArgumentParser(
        description='NVT5 - derive exact broker closed-bar cutoffs for Ground-Truth-required replay pairs.'
    )
    ap.add_argument('--ground-truth-dir', required=True)
    ap.add_argument('--cutoff-manifest', required=True)
    ap.add_argument('--input-dir', required=True)
    ap.add_argument('--broker-symbol', default='USDJPY#')
    ap.add_argument('--teacher-symbol', default='USDJPY')
    ap.add_argument('--output-tsv', required=True)
    ap.add_argument('--output-json', required=True)
    args = ap.parse_args()

    gt_dir = Path(args.ground_truth_dir)
    input_dir = Path(args.input_dir)
    manifest = load_json(Path(args.cutoff_manifest))

    date_by_source: dict[str, date] = {}
    for src in manifest.get('sources', []):
        source_id = str(src.get('source_id') or '')
        market_date = str(src.get('expected_last_market_date') or '')
        if not source_id or not market_date:
            raise ValueError('cutoff manifest source missing source_id/expected_last_market_date')
        date_by_source[source_id] = date.fromisoformat(market_date)

    pair_cases: dict[tuple[str, str], list[str]] = defaultdict(list)
    for path in sorted(gt_dir.glob('GT_*.json')):
        if path.name == 'GT_TEMPLATE.json':
            continue
        gt = load_json(path)
        if str(gt.get('symbol') or '') != args.teacher_symbol:
            continue
        case_id = str(gt.get('case_id') or path.stem)
        source_id = str(gt.get('source_id') or '')
        timeframe = str(gt.get('timeframe') or '')
        if not source_id or not timeframe:
            raise ValueError(f'missing source_id/timeframe in {path}')
        if source_id not in date_by_source:
            raise ValueError(f'no expected market date for {source_id}')
        pair_cases[(source_id, timeframe)].append(case_id)

    if not pair_cases:
        raise ValueError('no Ground-Truth-required replay pairs found')

    safe = safe_file_symbol(args.broker_symbol)
    rows: list[dict] = []
    for (source_id, timeframe), case_ids in sorted(pair_cases.items()):
        input_csv = input_dir / f'NVT_{safe}_{timeframe}.csv'
        if not input_csv.exists():
            raise FileNotFoundError(f'missing NVT deep-history CSV: {input_csv}')

        bars = load_ohlc_csv(input_csv)
        if not bars:
            raise ValueError(f'empty OHLC input: {input_csv}')

        target_date = date_by_source[source_id]
        same_day = [b for b in bars if b.time.date() == target_date]
        if not same_day:
            first_date = bars[0].time.date().isoformat()
            last_date = bars[-1].time.date().isoformat()
            raise ValueError(
                f'{source_id} {timeframe}: expected broker date {target_date.isoformat()} '
                f'not present in {input_csv}; available date range {first_date}..{last_date}'
            )

        last_bar = max(same_day, key=lambda b: b.time)
        future_count = sum(1 for b in bars if b.time > last_bar.time)
        frozen_count = sum(1 for b in bars if b.time <= last_bar.time)
        if frozen_count < 3:
            raise ValueError(f'{source_id} {timeframe}: fewer than 3 bars at resolved cutoff')

        rows.append({
            'source_id': source_id,
            'timeframe': timeframe,
            'target_market_date': target_date.isoformat(),
            'exact_cutoff': last_bar.time.isoformat(),
            'cases': ','.join(sorted(case_ids)),
            'input_csv': str(input_csv.resolve()),
            'input_first_bar': bars[0].time.isoformat(),
            'input_last_bar': bars[-1].time.isoformat(),
            'frozen_bar_count': frozen_count,
            'excluded_future_bar_count': future_count,
        })

    out_tsv = Path(args.output_tsv)
    out_tsv.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        'source_id', 'timeframe', 'target_market_date', 'exact_cutoff', 'cases',
        'input_csv', 'input_first_bar', 'input_last_bar', 'frozen_bar_count',
        'excluded_future_bar_count',
    ]
    with out_tsv.open('w', encoding='ascii', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'schema': 'nvt5-resolved-cutoffs/1.0',
        'status': 'PASS',
        'teacher_symbol': args.teacher_symbol,
        'broker_symbol': args.broker_symbol,
        'authority': 'ACTUAL_XM_CLOSED_BAR_HISTORY',
        'pair_count': len(rows),
        'case_count': sum(len(r['cases'].split(',')) for r in rows),
        'pairs': rows,
        'rules': {
            'date_source': str(Path(args.cutoff_manifest)),
            'exact_cutoff_rule': 'latest exported closed-bar timestamp whose broker date equals expected_last_market_date',
            'fallback_to_previous_date': False,
            'teacher_video_clock_used_as_market_clock': False,
        },
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'status': 'PASS',
        'pair_count': len(rows),
        'case_count': payload['case_count'],
        'output_tsv': str(out_tsv),
        'output_json': str(out_json),
        'resolved': [
            {
                'source_id': r['source_id'],
                'timeframe': r['timeframe'],
                'exact_cutoff': r['exact_cutoff'],
                'cases': r['cases'],
            }
            for r in rows
        ],
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
