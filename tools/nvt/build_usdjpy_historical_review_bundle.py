from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from live_draw.geometry import build_channel_candidates, select_large_mid
from live_draw.market_input import load_ohlc_csv
from live_draw.turn_detector import detect_turns

WINDOWS = {'D1': 90, 'H4': 180, 'H1': 240, 'M15': 320}
DEV_EXCLUDE_START = datetime(2026, 8, 1)
DEV_EXCLUDE_END = datetime(2026, 9, 15, 23, 59, 59)


def bar_row(b):
    return {
        'time': b.time.isoformat(),
        'open': b.open,
        'high': b.high,
        'low': b.low,
        'close': b.close,
        'volume': b.volume,
    }


def pivot_row(p):
    return {
        'kind': p.kind,
        'time': p.time.isoformat(),
        'price': p.price,
        'confirmed_by_time': p.confirmed_by_time.isoformat(),
        'retracement': p.retracement,
    }


def candidate_row(c):
    if c is None:
        return None
    return {
        'candidate_id': c.id_key,
        'direction': c.direction,
        'anchor1': pivot_row(c.anchor1),
        'anchor2': pivot_row(c.anchor2),
        'ch_anchor': pivot_row(c.ch_anchor),
        'slope_per_second': c.slope_per_second,
        'turn_span': c.turn_span,
        'tl_contacts': c.tl_contacts,
        'ch_contacts': c.ch_contacts,
        'unbroken_close': c.unbroken_close,
        'ch_offset': c.ch_offset,
        'zone_width': c.zone_width,
    }


def resolve_csv(input_dir: Path, tf: str) -> Path:
    preferred = [
        input_dir / f'NVT_USDJPY#_{tf}.csv',
        input_dir / f'NVT_USDJPY_{tf}.csv',
    ]
    for p in preferred:
        if p.exists():
            return p
    matches = sorted(input_dir.glob(f'NVT_USDJPY*_{tf}.csv'))
    if not matches:
        raise FileNotFoundError(f'No USDJPY NVT history CSV found for {tf} in {input_dir}')
    return matches[0]


def frozen_summary(symbol: str, tf: str, bars):
    turns = detect_turns(bars)
    candidates = build_channel_candidates(bars, turns.pivots)
    large, mid, audit = select_large_mid(symbol, tf, candidates)
    return {
        'closed_bar_count': len(bars),
        'effective_last_closed_bar': bars[-1].time.isoformat(),
        'confirmed_turn_count': len(turns.pivots),
        'active_leg': turns.active_leg,
        'active_threshold': turns.active_threshold,
        'recent_pivots': [pivot_row(p) for p in turns.pivots[-20:]],
        'baseline_large': candidate_row(large.candidate if large else None),
        'baseline_mid': candidate_row(mid.candidate if mid else None),
        'baseline_classifier_audit': audit,
    }


def weekly_candidates(h1_bars):
    by_week = {}
    for b in h1_bars:
        if DEV_EXCLUDE_START <= b.time <= DEV_EXCLUDE_END:
            continue
        iso = b.time.isocalendar()
        by_week[(iso.year, iso.week)] = b.time
    return sorted(by_week.values())


def evenly_pick(items, count):
    if len(items) <= count:
        return items
    if count <= 1:
        return [items[len(items) // 2]]
    idxs = []
    for i in range(count):
        idx = round(i * (len(items) - 1) / (count - 1))
        if idx not in idxs:
            idxs.append(idx)
    return [items[i] for i in idxs]


def main() -> int:
    ap = argparse.ArgumentParser(description='Build USDJPY future-hidden historical review bundle for ChatGPT + user adjudication.')
    ap.add_argument('--input-dir', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--case-count', type=int, default=8)
    ap.add_argument('--symbol', default='USDJPY#')
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    paths = {tf: resolve_csv(input_dir, tf) for tf in WINDOWS}
    all_bars = {tf: load_ohlc_csv(path) for tf, path in paths.items()}

    eligible = []
    for cutoff in weekly_candidates(all_bars['H1']):
        ok = True
        for tf, need in WINDOWS.items():
            if sum(1 for b in all_bars[tf] if b.time <= cutoff) < need:
                ok = False
                break
        if ok:
            eligible.append(cutoff)

    selected = evenly_pick(eligible, max(1, args.case_count))
    if not selected:
        raise ValueError('No eligible USDJPY historical cutoffs found outside the development-video window.')

    cases = []
    for i, cutoff in enumerate(selected, 1):
        tf_payload = {}
        for tf, window in WINDOWS.items():
            frozen = [b for b in all_bars[tf] if b.time <= cutoff]
            tf_payload[tf] = {
                'chart_window': [bar_row(b) for b in frozen[-window:]],
                'analysis': frozen_summary(args.symbol, tf, frozen),
            }

        cases.append({
            'case_id': f'USDJPY_HIST_{i:02d}',
            'cutoff': cutoff.isoformat(),
            'future_bars_included': False,
            'known_teacher_answer': None,
            'review_mode': 'CHATGPT_FIRST_USER_ADJUDICATION_ONLY_WHEN_NEEDED',
            'timeframes': tf_payload,
            'user_review_fields': {
                'structure_scale': None,
                'draw_or_no_line': None,
                'anchor1_ok': None,
                'anchor2_ok': None,
                'keep_old_reference': None,
                'suppress_short_lived_steep_line': None,
                'overall': None,
                'notes': None,
            },
        })

    payload = {
        'schema': 'nvt8h-usdjpy-historical-review-bundle/0.1',
        'status': 'RESEARCH_ONLY_HUMAN_ADJUDICATED_VALIDATION',
        'symbol_scope': 'USDJPY_ONLY',
        'purpose': 'Let ChatGPT perform the mechanical historical review first and surface only cases/fields that need user judgment.',
        'official_nvt8_strict_holdout': False,
        'why_not_strict_holdout': 'No teacher/video answer is available; this is supplemental historical operational validation.',
        'selection_policy': {
            'future_hidden': True,
            'cutoff_source': 'weekly latest H1 bar outside known video-development window',
            'development_exclusion_start': DEV_EXCLUDE_START.isoformat(),
            'development_exclusion_end': DEV_EXCLUDE_END.isoformat(),
            'requested_case_count': args.case_count,
            'generated_case_count': len(cases),
            'window_bars': WINDOWS,
        },
        'source_files': {tf: str(p) for tf, p in paths.items()},
        'review_protocol': [
            'ChatGPT renders/inspects each future-hidden D1/H4/H1/M15 case.',
            'ChatGPT applies current NVT6/NVT7 research semantics and flags only ambiguous or high-impact judgments.',
            'User judges only flagged items; unknown teacher answer remains explicit.',
            'Do not tune rules mid-case. Record PASS/FAIL/AMBIGUOUS first, then review aggregate failures later.',
        ],
        'cases': cases,
        'production_writeback': False,
        'normal_run_modified': False,
        'mt4_object_writeback': False,
        'trade_authority': False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'status': 'PASS',
        'output': str(out),
        'case_count': len(cases),
        'first_cutoff': cases[0]['cutoff'],
        'last_cutoff': cases[-1]['cutoff'],
        'future_hidden': True,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
