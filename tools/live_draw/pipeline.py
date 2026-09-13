from __future__ import annotations

import json
from pathlib import Path

from .geometry import build_channel_candidates, select_large_mid
from .lifecycle import load_state, promote_selection, save_state
from .market_input import load_ohlc_csv
from .snapshot import write_snapshot
from .turn_detector import detect_turns


def run_one_timeframe(
    input_csv: str | Path,
    symbol: str,
    timeframe: str,
    state_path: str | Path,
    snapshot_path: str | Path,
    audit_path: str | Path,
) -> dict:
    bars = load_ohlc_csv(input_csv)
    turns = detect_turns(bars)
    candidates = build_channel_candidates(bars, turns.pivots)
    large, mid, class_audit = select_large_mid(symbol, timeframe, candidates)

    state = load_state(state_path)
    changed = []
    for selected in (large, mid):
        if selected is None:
            continue
        state, did_change = promote_selection(state, selected)
        if did_change:
            changed.append(selected.level)
    save_state(state_path, state)
    snapshot_rows = write_snapshot(snapshot_path, state)

    audit = {
        'status': 'PASS',
        'mode': 'TEST',
        'symbol': symbol,
        'timeframe': timeframe,
        'bars': len(bars),
        'turn_detector': {
            'version': turns.detector_version,
            'status': turns.status,
            'confirmed_turns': len(turns.pivots),
            'active_leg': turns.active_leg,
            'active_threshold': turns.active_threshold,
        },
        'geometry': {
            'internal_candidates': len(candidates),
            'large_selected': large.candidate.id_key if large else None,
            'mid_selected': mid.candidate.id_key if mid else None,
            'classifier': class_audit,
        },
        'lifecycle_changed': changed,
        'snapshot_rows': snapshot_rows,
        'warnings': [
            'LARGE_MID_CLASSIFIER_IS_PROVISIONAL',
            'TL_UNBROKEN_CLOSE_IS_PROVISIONAL_SELECTION_EVIDENCE_NOT_FINAL_BREAK_DETECTOR',
            'SELECTION_USES_EXACT_CANDLE_INTERSECTION_CONTACTS_WITHOUT_FIXED_PIP_OR_ATR_THRESHOLD',
        ],
    }
    audit_path = Path(audit_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    return audit
