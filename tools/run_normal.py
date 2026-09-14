from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path

from live_draw.normal_run import (
    TFS,
    merge_rebuilt_states,
    normal_input_name,
    rebuild_timeframe_from_csv,
    safe_symbol_filename,
    validate_rebuilt_state,
)
from live_draw.snapshot import write_snapshot

SNAPSHOT_HEADER = [
    'object_id','symbol','timeframe','structure_level','role','t1','p1','t2','p2',
    'generation_role','generation','status','extent',
]
ALLOWED_ROLES = {'TL', 'CH', 'TL_ZONE_EDGE', 'CH_ZONE_EDGE'}


def validate_snapshot(path: Path, expected_symbol: str) -> dict:
    seen: set[str] = set()
    rows = 0
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != SNAPSHOT_HEADER:
            raise ValueError(f'bad snapshot header: {reader.fieldnames}')
        for row in reader:
            rows += 1
            oid = row['object_id']
            if not oid or oid in seen:
                raise ValueError(f'duplicate/empty object_id: {oid!r}')
            seen.add(oid)
            if row['symbol'] != expected_symbol:
                raise ValueError(f'snapshot symbol mismatch: {row["symbol"]}')
            if row['timeframe'] not in TFS:
                raise ValueError(f'bad timeframe: {row["timeframe"]}')
            if row['role'] not in ALLOWED_ROLES:
                raise ValueError(f'bad role: {row["role"]}')
            float(row['p1'])
            float(row['p2'])
    if rows == 0:
        raise ValueError('snapshot has no drawing rows')
    return {'status': 'PASS', 'rows': rows, 'unique_object_ids': len(seen)}


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def publish_validated_snapshot(path: Path, state: dict, expected_symbol: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        write_snapshot(tmp, state)
        validation = validate_snapshot(tmp, expected_symbol)
        os.replace(tmp, path)
        return validation
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description='NCA Normal Run - XM symbol history rebuild')
    ap.add_argument('--symbol', required=True, help='Exact XM MT4 symbol name, e.g. GOLD#')
    ap.add_argument('--input-dir', required=True, help='MT4 Common Files live_input directory')
    ap.add_argument('--output-dir', required=True, help='MT4 Common Files live_output directory')
    args = ap.parse_args()

    symbol = args.symbol.strip()
    if not symbol:
        raise SystemExit('--symbol must be non-empty')
    safe = safe_symbol_filename(symbol)
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    final_state = output_dir / f'NORMAL_{safe}_live_state.json'
    final_snapshot = output_dir / f'NORMAL_{safe}_live_snapshot.csv'
    final_audit = output_dir / f'NORMAL_{safe}_run_audit.json'

    rebuilt_states = []
    timeframe_audits = {}
    missing = []

    for tf in TFS:
        src = input_dir / normal_input_name(symbol, tf)
        if not src.exists():
            missing.append(str(src))
            continue
        try:
            tf_state, tf_audit = rebuild_timeframe_from_csv(src, symbol, tf)
            rebuilt_states.append(tf_state)
            timeframe_audits[tf] = tf_audit
        except Exception as exc:
            timeframe_audits[tf] = {
                'status': 'ERROR',
                'error': f'{type(exc).__name__}: {exc}',
                'input': str(src),
            }

    if missing or any(a.get('status') == 'ERROR' for a in timeframe_audits.values()):
        overall = {
            'status': 'FAIL_KEEP_LAST_VALID_DRAWING',
            'mode': 'NORMAL_RUN',
            'symbol': symbol,
            'missing_inputs': missing,
            'timeframes': timeframe_audits,
            'snapshot_published': False,
        }
        atomic_write_json(final_audit, overall)
        print(json.dumps(overall, ensure_ascii=False, indent=2))
        return 2 if missing else 1

    try:
        rebuilt = merge_rebuilt_states(rebuilt_states)
        state_validation = validate_rebuilt_state(rebuilt, symbol)

        # State is rebuilt from scratch every Normal Run. Persist it for audit,
        # but never use it as authority for the next run's `previous`.
        atomic_write_json(final_state, rebuilt)

        # The old published snapshot remains untouched until the new temp
        # snapshot passes validation. os.replace performs the publication.
        snapshot_validation = publish_validated_snapshot(final_snapshot, rebuilt, symbol)

        overall = {
            'status': 'PASS',
            'mode': 'NORMAL_RUN',
            'symbol': symbol,
            'timeframes': timeframe_audits,
            'state_validation': state_validation,
            'snapshot_validation': snapshot_validation,
            'snapshot_published': True,
            'state': str(final_state),
            'snapshot': str(final_snapshot),
            'trade_fields_emitted': False,
            'noda_engine_writeback': False,
            'chatgpt_runtime_dependency': False,
            'tc_dependency': False,
        }
        atomic_write_json(final_audit, overall)
        print(json.dumps(overall, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        overall = {
            'status': 'FAIL_KEEP_LAST_VALID_DRAWING',
            'mode': 'NORMAL_RUN',
            'symbol': symbol,
            'error': f'{type(exc).__name__}: {exc}',
            'timeframes': timeframe_audits,
            'snapshot_published': False,
        }
        atomic_write_json(final_audit, overall)
        print(json.dumps(overall, ensure_ascii=False, indent=2))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
