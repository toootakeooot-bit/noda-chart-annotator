from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


def _line_from_state(s: dict, role: str) -> tuple[datetime, float, datetime, float]:
    t1 = datetime.fromisoformat(s['anchor1_time'])
    t2 = datetime.fromisoformat(s['anchor2_time'])
    p1 = float(s['anchor1_price'])
    p2 = float(s['anchor2_price'])
    offset = float(s['ch_offset'])
    width = float(s['zone_width'])
    direction = s['direction']

    if role == 'TL':
        return t1, p1, t2, p2
    if role == 'CH':
        return t1, p1 + offset, t2, p2 + offset
    if role == 'TL_ZONE_EDGE':
        z = width if direction == 'RISING' else -width
        return t1, p1 + z, t2, p2 + z
    if role == 'CH_ZONE_EDGE':
        z = -width if direction == 'RISING' else width
        return t1, p1 + offset + z, t2, p2 + offset + z
    raise ValueError(role)


def write_snapshot(path: str | Path, state: dict) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[list[str]] = []
    for _, slot in sorted(state.get('slots', {}).items()):
        for generation_role in ('previous', 'current'):
            s = slot.get(generation_role)
            if not s:
                continue
            for role in ('TL', 'CH', 'TL_ZONE_EDGE', 'CH_ZONE_EDGE'):
                t1, p1, t2, p2 = _line_from_state(s, role)
                rows.append([
                    f"{s['line_id']}__{role}", s['symbol'], s['timeframe'], s['structure_level'], role,
                    t1.strftime('%Y-%m-%d %H:%M:%S'), f'{p1:.8f}',
                    t2.strftime('%Y-%m-%d %H:%M:%S'), f'{p2:.8f}',
                    generation_role.upper(), str(s['generation']), s['status'], 'RAY_RIGHT',
                ])
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['object_id','symbol','timeframe','structure_level','role','t1','p1','t2','p2','generation_role','generation','status','extent'])
        w.writerows(rows)
    return len(rows)
