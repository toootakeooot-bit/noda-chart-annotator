from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .model import Bar

TIME_FORMATS = (
    '%Y-%m-%d %H:%M:%S',
    '%Y.%m.%d %H:%M:%S',
    '%Y-%m-%dT%H:%M:%S',
)


def parse_time(value: str) -> datetime:
    value = value.strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return datetime.fromisoformat(value)


def load_ohlc_csv(path: str | Path) -> list[Bar]:
    path = Path(path)
    rows: list[Bar] = []
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        required = {'time', 'open', 'high', 'low', 'close'}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'Missing OHLC fields: {sorted(missing)}')
        for row in reader:
            rows.append(
                Bar(
                    time=parse_time(row['time']),
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row.get('volume') or 0.0),
                )
            )
    rows.sort(key=lambda x: x.time)
    for i, bar in enumerate(rows):
        if bar.low > min(bar.open, bar.close, bar.high):
            raise ValueError(f'Invalid low at row {i}')
        if bar.high < max(bar.open, bar.close, bar.low):
            raise ValueError(f'Invalid high at row {i}')
        if i and bar.time <= rows[i - 1].time:
            raise ValueError('OHLC times must be strictly increasing')
    return rows


def write_ohlc_csv(path: str | Path, bars: Iterable[Bar]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time', 'open', 'high', 'low', 'close', 'volume'])
        for b in bars:
            writer.writerow([
                b.time.strftime('%Y-%m-%d %H:%M:%S'),
                f'{b.open:.10f}'.rstrip('0').rstrip('.'),
                f'{b.high:.10f}'.rstrip('0').rstrip('.'),
                f'{b.low:.10f}'.rstrip('0').rstrip('.'),
                f'{b.close:.10f}'.rstrip('0').rstrip('.'),
                b.volume,
            ])
