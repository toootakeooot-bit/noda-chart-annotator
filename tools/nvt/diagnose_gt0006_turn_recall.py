from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from live_draw.geometry import build_channel_candidates, line_value  # noqa: E402
from live_draw.market_input import load_ohlc_csv  # noqa: E402
from live_draw.turn_detector import detect_turns  # noqa: E402


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def find_frozen_csv(replay_root: Path, source_id: str, timeframe: str) -> Path:
    source_dir = replay_root / source_id
    if not source_dir.exists():
        raise FileNotFoundError(f'replay source directory not found: {source_dir}')
    matches = sorted(source_dir.glob(f'*_{timeframe}_frozen.csv'))
    if not matches:
        matches = sorted(source_dir.glob(f'*{timeframe}*frozen.csv'))
    if len(matches) != 1:
        raise RuntimeError(
            f'expected exactly one frozen {timeframe} CSV under {source_dir}; found {len(matches)}: '
            + ', '.join(str(p) for p in matches)
        )
    return matches[0]


def in_window(t: datetime, start: datetime, end: datetime) -> bool:
    return start <= t <= end


def local_extrema_indices(bars, left: int, right: int, kind: str) -> list[int]:
    out: list[int] = []
    for i in range(left, len(bars) - right):
        if kind == 'HIGH':
            center = bars[i].high
            lhs = [bars[j].high for j in range(i - left, i)]
            rhs = [bars[j].high for j in range(i + 1, i + right + 1)]
            if center >= max(lhs) and center >= max(rhs) and (center > max(lhs) or center > max(rhs)):
                out.append(i)
        else:
            center = bars[i].low
            lhs = [bars[j].low for j in range(i - left, i)]
            rhs = [bars[j].low for j in range(i + 1, i + right + 1)]
            if center <= min(lhs) and center <= min(rhs) and (center < min(lhs) or center < min(rhs)):
                out.append(i)
    return out


def nearest_before(indices: list[int], i: int) -> int | None:
    vals = [x for x in indices if x < i]
    return vals[-1] if vals else None


def nearest_after(indices: list[int], i: int) -> int | None:
    for x in indices:
        if x > i:
            return x
    return None


def pivot_dict(p) -> dict:
    return {
        'kind': p.kind,
        'time': p.time.isoformat(),
        'price': p.price,
        'bar_index': p.bar_index,
        'confirmed_by_time': p.confirmed_by_time.isoformat(),
        'retracement': p.retracement,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Research-only diagnosis for GT_0006 H1 candidate-recall gap.'
    )
    ap.add_argument('--replay-root', required=True)
    ap.add_argument('--source-id', default='NVT_VIDEO_20260912')
    ap.add_argument('--timeframe', default='H1')
    ap.add_argument('--window-start', default='2026-09-01T00:00:00')
    ap.add_argument('--window-end', default='2026-09-11T23:00:00')
    ap.add_argument('--anchor1-start', default='2026-09-01T00:00:00')
    ap.add_argument('--anchor1-end', default='2026-09-03T23:59:59')
    ap.add_argument('--anchor2-start', default='2026-09-04T00:00:00')
    ap.add_argument('--anchor2-end', default='2026-09-11T23:00:00')
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    replay_root = Path(args.replay_root)
    frozen_csv = find_frozen_csv(replay_root, args.source_id, args.timeframe)
    bars = load_ohlc_csv(frozen_csv)
    if len(bars) < 3:
        raise ValueError('frozen replay contains fewer than 3 bars')

    window_start, window_end = dt(args.window_start), dt(args.window_end)
    a1_start, a1_end = dt(args.anchor1_start), dt(args.anchor1_end)
    a2_start, a2_end = dt(args.anchor2_start), dt(args.anchor2_end)

    full_turns = detect_turns(bars)
    full_candidates = build_channel_candidates(bars, full_turns.pivots)
    confirmed_highs = [p for p in full_turns.pivots if p.kind == 'HIGH']
    confirmed_lows = [p for p in full_turns.pivots if p.kind == 'LOW']
    confirmed_high_by_time = {p.time: p for p in confirmed_highs}
    candidate_ids = {c.id_key for c in full_candidates}

    # Two neutral, research-only local-extrema lenses.  They do not change or
    # replace the production 38% detector; they only expose visually obvious
    # small-Dow-like highs that production may suppress.
    highs_l1 = local_extrema_indices(bars, 1, 1, 'HIGH')
    lows_l1 = local_extrema_indices(bars, 1, 1, 'LOW')
    highs_l2 = set(local_extrema_indices(bars, 2, 2, 'HIGH'))

    # Prefix replay gives the exact production detector state at each bar
    # without instrumenting or modifying production code.
    states = {}
    for i, bar in enumerate(bars):
        if window_start <= bar.time <= window_end:
            states[i] = detect_turns(bars[: i + 1])

    local_high_rows: list[dict] = []
    for i in highs_l1:
        bar = bars[i]
        if not in_window(bar.time, window_start, window_end):
            continue
        st = states.get(i)
        if st is None:
            continue
        confirmed = confirmed_high_by_time.get(bar.time)
        active_extreme_time = None
        if st.active_extreme_index is not None:
            active_extreme_time = bars[st.active_extreme_index].time

        prev_low_i = nearest_before(lows_l1, i)
        next_low_i = nearest_after(lows_l1, i)
        micro_lower_low = False
        if prev_low_i is not None and next_low_i is not None:
            micro_lower_low = bars[next_low_i].low < bars[prev_low_i].low

        if confirmed is not None:
            reason = 'CONFIRMED_HIGH_PIVOT'
        elif st.active_leg != 'RISING':
            reason = 'LOCAL_HIGH_INSIDE_PRODUCTION_FALLING_LEG'
        elif active_extreme_time != bar.time:
            reason = 'LOCAL_HIGH_NOT_ACTIVE_RISING_EXTREME'
        else:
            replacement_time = None
            for j in range(i + 1, len(bars)):
                if bars[j].time > window_end:
                    break
                future = states.get(j)
                if future is None:
                    future = detect_turns(bars[: j + 1])
                if future.active_leg == 'RISING' and future.active_extreme_index is not None:
                    ft = bars[future.active_extreme_index].time
                    if ft != bar.time and bars[future.active_extreme_index].high > bar.high:
                        replacement_time = ft
                        break
            reason = (
                'ACTIVE_HIGH_REPLACED_BEFORE_CONFIRMATION'
                if replacement_time is not None
                else 'ACTIVE_HIGH_NOT_CONFIRMED_BY_CUTOFF'
            )

        retrace_fraction = None
        threshold_at_high = st.active_threshold
        start_time = None
        start_price = None
        if (
            st.active_leg == 'RISING'
            and st.active_start_index is not None
            and st.active_extreme_index == i
        ):
            start = bars[st.active_start_index]
            start_time = start.time.isoformat()
            start_price = start.low
            amplitude = bar.high - start.low
            if amplitude > 0:
                stop = len(bars)
                for j in range(i + 1, len(bars)):
                    if bars[j].high > bar.high:
                        stop = j
                        break
                future_closes = [b.close for b in bars[i + 1 : stop] if b.time <= window_end]
                if future_closes:
                    retrace_fraction = (bar.high - min(future_closes)) / amplitude

        local_high_rows.append({
            'time': bar.time.isoformat(),
            'high': bar.high,
            'close': bar.close,
            'is_l2r2_local_high': i in highs_l2,
            'production_confirmed_high': confirmed is not None,
            'production_confirmed_by_time': confirmed.confirmed_by_time.isoformat() if confirmed else None,
            'production_state_at_bar': {
                'active_leg': st.active_leg,
                'active_extreme_time': active_extreme_time.isoformat() if active_extreme_time else None,
                'active_threshold': threshold_at_high,
                'active_start_time': start_time,
                'active_start_price': start_price,
            },
            'diagnostic_reason': reason,
            'max_close_retracement_fraction_before_higher_high_or_cutoff': retrace_fraction,
            'micro_dow_context': {
                'previous_local_low_time': bars[prev_low_i].time.isoformat() if prev_low_i is not None else None,
                'previous_local_low': bars[prev_low_i].low if prev_low_i is not None else None,
                'next_local_low_time': bars[next_low_i].time.isoformat() if next_low_i is not None else None,
                'next_local_low': bars[next_low_i].low if next_low_i is not None else None,
                'next_low_breaks_previous_low': micro_lower_low,
                'research_label': 'LOW_HIGH_LOWER_LOW' if micro_lower_low else None,
            },
        })

    a1_confirmed = [p for p in confirmed_highs if in_window(p.time, a1_start, a1_end)]
    a2_confirmed = [p for p in confirmed_highs if in_window(p.time, a2_start, a2_end)]
    pair_rows: list[dict] = []
    for a in a1_confirmed:
        for b in a2_confirmed:
            if b.time <= a.time:
                continue
            candidate_id = f'FALLING:{a.time.isoformat()}:{b.time.isoformat()}'
            if b.price >= a.price:
                gate = 'REJECT_SECOND_HIGH_NOT_LOWER'
            else:
                valid_opp = [p for p in confirmed_lows if p.time >= a.time]
                ch_ok = False
                for p in valid_opp:
                    slope = (b.price - a.price) / (b.time - a.time).total_seconds()
                    base_y = line_value(p.time, a.time, a.price, slope)
                    if p.price - base_y < 0:
                        ch_ok = True
                        break
                if not ch_ok:
                    gate = 'REJECT_NO_VALID_FALLING_CH_OFFSET'
                elif candidate_id in candidate_ids:
                    gate = 'PRESENT_IN_CANDIDATE_POOL'
                else:
                    gate = 'UNEXPECTED_GENERATOR_ABSENCE'
            pair_rows.append({
                'anchor1': pivot_dict(a),
                'anchor2': pivot_dict(b),
                'candidate_id': candidate_id,
                'gate_result': gate,
            })

    micro_a1 = [r for r in local_high_rows if in_window(dt(r['time']), a1_start, a1_end)]
    micro_a2 = [r for r in local_high_rows if in_window(dt(r['time']), a2_start, a2_end)]
    teacher_like_micro_pairs: list[dict] = []
    for a in micro_a1:
        for b in micro_a2:
            if b['high'] >= a['high']:
                continue
            if not a['micro_dow_context']['next_low_breaks_previous_low']:
                continue
            if not b['micro_dow_context']['next_low_breaks_previous_low']:
                continue
            teacher_like_micro_pairs.append({
                'anchor1_time': a['time'],
                'anchor1_high': a['high'],
                'anchor1_production_confirmed': a['production_confirmed_high'],
                'anchor2_time': b['time'],
                'anchor2_high': b['high'],
                'anchor2_production_confirmed': b['production_confirmed_high'],
                'both_confirmed_for_production_candidate': (
                    a['production_confirmed_high'] and b['production_confirmed_high']
                ),
            })

    reason_counts: dict[str, int] = {}
    for row in local_high_rows:
        reason_counts[row['diagnostic_reason']] = reason_counts.get(row['diagnostic_reason'], 0) + 1

    if teacher_like_micro_pairs and not any(
        r['gate_result'] == 'PRESENT_IN_CANDIDATE_POOL' for r in pair_rows
    ):
        primary = 'TURN_OR_SCALE_RECALL_GAP_LIKELY'
    elif any(r['gate_result'].startswith('REJECT_') for r in pair_rows):
        primary = 'CANDIDATE_GENERATOR_GATE_GAP_POSSIBLE'
    elif any(r['gate_result'] == 'PRESENT_IN_CANDIDATE_POOL' for r in pair_rows):
        primary = 'CANDIDATE_PRESENT_RECHECK_TEACHER_WINDOWS_OR_SELECTOR'
    else:
        primary = 'INSUFFICIENT_EVIDENCE'

    payload = {
        'schema': 'nvt-gt0006-turn-recall-diagnostic/1.0',
        'mode': 'READ_ONLY_RESEARCH',
        'case_id': 'GT_0006',
        'source_id': args.source_id,
        'timeframe': args.timeframe,
        'source_frozen_csv': str(frozen_csv),
        'window': {'start': args.window_start, 'end': args.window_end},
        'teacher_anchor_windows': {
            'anchor1': {'start': args.anchor1_start, 'end': args.anchor1_end},
            'anchor2': {'start': args.anchor2_start, 'end': args.anchor2_end},
        },
        'production_detector': {
            'version': full_turns.detector_version,
            'retracement': 0.38,
            'confirmed_turn_count_total': len(full_turns.pivots),
            'candidate_count_total': len(full_candidates),
        },
        'summary': {
            'local_high_count_in_window': len(local_high_rows),
            'confirmed_high_count_in_window': sum(
                1 for p in confirmed_highs if in_window(p.time, window_start, window_end)
            ),
            'diagnostic_reason_counts': reason_counts,
            'confirmed_highs_in_anchor1_window': len(a1_confirmed),
            'confirmed_highs_in_anchor2_window': len(a2_confirmed),
            'confirmed_pair_gate_rows': len(pair_rows),
            'teacher_like_micro_pair_count': len(teacher_like_micro_pairs),
            'primary_diagnosis': primary,
        },
        'local_highs': local_high_rows,
        'confirmed_pair_gate_analysis': pair_rows,
        'teacher_like_micro_pairs': teacher_like_micro_pairs[:200],
        'research_only_improvement_hypotheses': [
            {
                'id': 'H1_NESTED_MICRO_DOW',
                'idea': 'Keep production 38% pivots, but add a separate micro-Dow layer where a local rebound high can be structurally validated when a later local low breaks the preceding local low.',
                'risk': 'Can overproduce pivots unless minimum separation and structure ownership are gated.',
            },
            {
                'id': 'H2_PROVISIONAL_PIVOT_POOL',
                'idea': 'Allow unconfirmed local highs/lows into a research-only provisional candidate pool; promote only after structural confirmation.',
                'risk': 'Candidate explosion; must remain distinct from confirmed production pivots.',
            },
            {
                'id': 'H3_MULTI_SCALE_TURN',
                'idea': 'Run confirmed large/mid pivots and nested small-Dow pivots as separate scales instead of forcing one active leg to represent all structure.',
                'risk': 'Needs explicit scale ownership to prevent duplicate lines across H1/M15.',
            },
            {
                'id': 'H4_CLUSTER_EDGE',
                'idea': 'Group nearby same-side pivot highs/lows into clusters and preserve left/right edge metadata so teacher-preferred cluster-right-edge anchors can be selected later.',
                'risk': 'Tolerance must be price-structure based; do not hard-code a fixed pip distance globally.',
            },
            {
                'id': 'H5_WICK_OUTLIER_TAG',
                'idea': 'Tag extreme wick anchors as potential outliers instead of always accepting or deleting them; let later selector logic choose body/wick contextually.',
                'risk': 'Must not silently rewrite OHLC or teacher evidence.',
            },
        ],
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
        'case_id': 'GT_0006',
        'output': str(out),
        'primary_diagnosis': primary,
        'local_highs': len(local_high_rows),
        'confirmed_highs_anchor1': len(a1_confirmed),
        'confirmed_highs_anchor2': len(a2_confirmed),
        'teacher_like_micro_pairs': len(teacher_like_micro_pairs),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
