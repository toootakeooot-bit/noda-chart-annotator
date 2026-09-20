from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .model import LineSetState, SelectedStructure


def _now() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _same_geometry(state: dict, selected: SelectedStructure) -> bool:
    c = selected.candidate
    return (
        state.get('anchor1_time') == c.anchor1.time.isoformat()
        and state.get('anchor1_price') == c.anchor1.price
        and state.get('anchor2_time') == c.anchor2.time.isoformat()
        and state.get('anchor2_price') == c.anchor2.price
        and state.get('direction') == c.direction
    )


def load_state(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {'schema': 'nca-live-state/1.0', 'slots': {}}
    return json.loads(path.read_text(encoding='utf-8'))


def save_state(path: str | Path, state: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def promote_selection(state: dict, selected: SelectedStructure) -> tuple[dict, bool]:
    """Keep current + immediately previous TL set only.

    New geometry is based on confirmed turns; Break alone never deletes or
    replaces a TL here. CH-only movement may update the offset under one TL.
    """
    key = f'{selected.symbol}|{selected.timeframe}|{selected.level}'
    slot = state.setdefault('slots', {}).setdefault(key, {'current': None, 'previous': None, 'history': []})
    current = slot.get('current')

    if current and _same_geometry(current, selected):
        current['ch_offset'] = selected.candidate.ch_offset
        current['zone_width'] = selected.candidate.zone_width
        current['selection_version'] = selected.selection_version
        return state, False

    generation = (current.get('generation', 0) + 1) if current else 1
    line_id = f'NCA_{selected.symbol}_{selected.timeframe}_{selected.level}_G{generation:03d}'
    c = selected.candidate
    new_state = LineSetState(
        line_id=line_id,
        symbol=selected.symbol,
        timeframe=selected.timeframe,
        structure_level=selected.level,
        generation=generation,
        status='ACTIVE',
        direction=c.direction,
        anchor1_time=c.anchor1.time.isoformat(),
        anchor1_price=c.anchor1.price,
        anchor2_time=c.anchor2.time.isoformat(),
        anchor2_price=c.anchor2.price,
        ch_offset=c.ch_offset,
        zone_width=c.zone_width,
        selection_version=selected.selection_version,
        created_at=_now(),
        decision_hl_time=(c.decision_hl.time.isoformat() if c.decision_hl else None),
        decision_hl_price=(float(c.decision_hl.price) if c.decision_hl else None),
        decision_hl_kind=(c.decision_hl.kind if c.decision_hl else None),
        hl_break_time=(c.hl_break_time.isoformat() if c.hl_break_time else None),
        hl_break_mode=c.hl_break_mode,
    ).to_dict()

    if current:
        current = dict(current)
        current['status'] = 'RETIRED'
        current['replaced_at'] = _now()
        current['replacement_line_id'] = line_id
        if slot.get('previous'):
            slot['history'].append(slot['previous'])
        slot['previous'] = current
    slot['current'] = new_state
    return state, True
