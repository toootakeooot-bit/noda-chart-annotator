from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Literal, Optional

PivotKind = Literal['HIGH', 'LOW']
Direction = Literal['RISING', 'FALLING']
StructureLevel = Literal['LARGE_DOW', 'MID_DOW']
LineStatus = Literal['ACTIVE', 'BROKEN_WAIT_TURN', 'RETIRED']


@dataclass(frozen=True)
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class Pivot:
    kind: PivotKind
    bar_index: int
    time: datetime
    price: float
    confirmed_by_index: int
    confirmed_by_time: datetime
    retracement: float = 0.38


@dataclass(frozen=True)
class ChannelCandidate:
    direction: Direction
    anchor1: Pivot
    anchor2: Pivot
    slope_per_second: float
    turn_span: int
    tl_contacts: int
    ch_contacts: int
    unbroken_close: bool
    ch_anchor: Pivot
    ch_offset: float
    zone_width: float
    decision_hl: Optional[Pivot] = None
    hl_break_time: Optional[datetime] = None
    hl_break_mode: Optional[str] = None

    @property
    def id_key(self) -> str:
        return f'{self.direction}:{self.anchor1.time.isoformat()}:{self.anchor2.time.isoformat()}'


@dataclass(frozen=True)
class SelectedStructure:
    symbol: str
    timeframe: str
    level: StructureLevel
    candidate: ChannelCandidate
    selection_version: str = 'PROVISIONAL_EXACT_INTERSECTION_0.1'


@dataclass
class LineSetState:
    line_id: str
    symbol: str
    timeframe: str
    structure_level: StructureLevel
    generation: int
    status: LineStatus
    direction: Direction
    anchor1_time: str
    anchor1_price: float
    anchor2_time: str
    anchor2_price: float
    ch_offset: float
    zone_width: float
    selection_version: str
    created_at: str
    decision_hl_time: Optional[str] = None
    decision_hl_price: Optional[float] = None
    decision_hl_kind: Optional[PivotKind] = None
    hl_break_time: Optional[str] = None
    hl_break_mode: Optional[str] = None
    replaced_at: Optional[str] = None
    replacement_line_id: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)
