from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import sys

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from live_draw.geometry import build_channel_candidates, select_large_mid  # noqa: E402
from live_draw.market_input import load_ohlc_csv, write_ohlc_csv  # noqa: E402
from live_draw.normal_run import TFS  # noqa: E402
from live_draw.turn_detector import detect_turns  # noqa: E402


def parse_cutoff(value: str) -> datetime:
    value = value.strip()
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return datetime.fromisoformat(value)


def safe_name(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', '_', value.strip())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description='NVT5 - create deterministic time-frozen replay input and audit manifest')
    ap.add_argument('--input-csv', required=True)
    ap.add_argument('--symbol', required=True)
    ap.add_argument('--timeframe', required=True, choices=TFS)
    ap.add_argument('--cutoff', required=True, help='Verified ISO-8601 market-data cutoff')
    ap.add_argument('--case-id', required=True)
    ap.add_argument('--output-dir', required=True)
    args = ap.parse_args()

    src = Path(args.input_csv)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cutoff = parse_cutoff(args.cutoff)
    bars = load_ohlc_csv(src)
    if not bars:
        raise ValueError('source OHLC is empty')
    if (bars[0].time.tzinfo is None) != (cutoff.tzinfo is None):
        raise ValueError('cutoff timezone awareness must match OHLC timestamps')

    frozen = [b for b in bars if b.time <= cutoff]
    future = [b for b in bars if b.time > cutoff]
    if len(frozen) < 3:
        raise ValueError('fewer than 3 closed bars remain at cutoff')
    if frozen[-1].time > cutoff:
        raise AssertionError('look-ahead guard failed: frozen input contains future bar')

    safe = safe_name(args.symbol)
    stem = f'{safe_name(args.case_id)}_{safe}_{args.timeframe}'
    frozen_csv = out_dir / f'{stem}_frozen.csv'
    manifest_path = out_dir / f'{stem}_replay.json'
    write_ohlc_csv(frozen_csv, frozen)

    # Compute the current baseline result on the frozen bars for audit. This is
    # research output only and does not write production state/snapshot/MT4 objects.
    turns = detect_turns(frozen)
    candidates = build_channel_candidates(frozen, turns.pivots)
    large, mid, classifier = select_large_mid(args.symbol, args.timeframe, candidates)

    payload = {
        'schema': 'nvt-time-frozen-replay/1.0',
        'mode': 'READ_ONLY_RESEARCH',
        'case_id': args.case_id,
        'symbol': args.symbol,
        'timeframe': args.timeframe,
        'requested_cutoff': args.cutoff,
        'effective_last_closed_bar': frozen[-1].time.isoformat(),
        'first_frozen_bar': frozen[0].time.isoformat(),
        'frozen_bar_count': len(frozen),
        'excluded_future_bar_count': len(future),
        'look_ahead_guard': 'PASS',
        'source_csv': str(src),
        'source_sha256': sha256_file(src),
        'frozen_csv': str(frozen_csv),
        'frozen_sha256': sha256_file(frozen_csv),
        'detector': {
            'version': turns.detector_version,
            'status': turns.status,
            'confirmed_turn_count': len(turns.pivots),
            'active_leg': turns.active_leg,
            'active_threshold': turns.active_threshold,
        },
        'candidate_count': len(candidates),
        'baseline_selected_large_candidate_id': large.candidate.id_key if large else None,
        'baseline_selected_mid_candidate_id': mid.candidate.id_key if mid else None,
        'classifier_audit': classifier,
        'production_writeback': False,
        'snapshot_writeback': False,
        'mt4_object_writeback': False,
        'trade_authority': False,
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'status': 'PASS',
        'case_id': args.case_id,
        'timeframe': args.timeframe,
        'cutoff': args.cutoff,
        'effective_last_closed_bar': payload['effective_last_closed_bar'],
        'frozen_bar_count': len(frozen),
        'excluded_future_bar_count': len(future),
        'look_ahead_guard': 'PASS',
        'frozen_csv': str(frozen_csv),
        'manifest': str(manifest_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
