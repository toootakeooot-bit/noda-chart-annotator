from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .geometry import build_channel_candidates, line_value, select_large_mid
from .turn_detector import detect_turns


@dataclass(frozen=True)
class TLTransitionResolution:
    state: str
    reason_code: str
    active_candidate: object | None
    broken_candidate: object | None
    break_time: datetime | None
    confirmed_pivot_count: int
    candidate_count: int

    def to_audit_dict(self) -> dict:
        def cand(c):
            if c is None:
                return None
            return {
                "candidate_id": c.id_key,
                "direction": c.direction,
                "anchor1_time": c.anchor1.time.isoformat(),
                "anchor1_price": float(c.anchor1.price),
                "anchor2_time": c.anchor2.time.isoformat(),
                "anchor2_price": float(c.anchor2.price),
                "decision_hl_time": (
                    c.decision_hl.time.isoformat() if c.decision_hl else None
                ),
                "decision_hl_price": (
                    float(c.decision_hl.price) if c.decision_hl else None
                ),
                "hl_break_time": (
                    c.hl_break_time.isoformat() if c.hl_break_time else None
                ),
                "unbroken_close": bool(c.unbroken_close),
                "turn_span": int(c.turn_span),
                "tl_contacts": int(c.tl_contacts),
                "ch_contacts": int(c.ch_contacts),
            }
        return {
            "state": self.state,
            "reason_code": self.reason_code,
            "active_candidate": cand(self.active_candidate),
            "broken_candidate": cand(self.broken_candidate),
            "break_time": self.break_time.isoformat() if self.break_time else None,
            "confirmed_pivot_count": self.confirmed_pivot_count,
            "candidate_count": self.candidate_count,
        }


def _geometry_matches_state(candidate, state: dict | None) -> bool:
    if not state:
        return False
    return (
        state.get("direction") == candidate.direction
        and state.get("anchor1_time") == candidate.anchor1.time.isoformat()
        and abs(float(state.get("anchor1_price", 0.0)) - float(candidate.anchor1.price)) <= 1e-9
        and state.get("anchor2_time") == candidate.anchor2.time.isoformat()
        and abs(float(state.get("anchor2_price", 0.0)) - float(candidate.anchor2.price)) <= 1e-9
    )


def _first_break_after_anchor2(candidate, bars) -> datetime | None:
    for bar in bars[candidate.anchor2.bar_index + 1:]:
        y = line_value(
            bar.time,
            candidate.anchor1.time,
            candidate.anchor1.price,
            candidate.slope_per_second,
        )
        if candidate.direction == "RISING" and bar.close < y:
            return bar.time
        if candidate.direction == "FALLING" and bar.close > y:
            return bar.time
    return None


def resolve_tl_transition_from_candidates(
    bars,
    symbol: str,
    timeframe: str,
    candidates,
    confirmed_pivot_count: int,
    selected_state: dict | None = None,
    candidate_anchor_floor: datetime | None = None,
) -> TLTransitionResolution:
    """Pure post-selector state resolution over an already-built candidate set.

    candidate_anchor_floor limits STRUCTURE SELECTION to the requested window.
    Older bars may be present only to initialize the Turn detector; a candidate
    whose first or second TL anchor predates the floor is never eligible.
    """
    if candidate_anchor_floor is not None:
        candidates = [
            c for c in candidates
            if c.anchor1.time >= candidate_anchor_floor
            and c.anchor2.time >= candidate_anchor_floor
            and (
                c.decision_hl is None
                or c.decision_hl.time >= candidate_anchor_floor
            )
        ]
    large, _, _ = select_large_mid(symbol, timeframe, candidates)
    active_candidate = large.candidate if large is not None else None

    broken = [
        (c, _first_break_after_anchor2(c, bars))
        for c in candidates
        if not c.unbroken_close
    ]
    broken = [(c, t) for c, t in broken if t is not None]
    broken.sort(
        key=lambda item: (
            item[1],
            item[0].anchor2.time,
            item[0].turn_span,
        )
    )
    latest_broken = broken[-1] if broken else (None, None)

    if active_candidate is not None:
        if _geometry_matches_state(active_candidate, selected_state):
            return TLTransitionResolution(
                state="ACTIVE",
                reason_code="SELECTED_TL_STILL_UNBROKEN",
                active_candidate=active_candidate,
                broken_candidate=latest_broken[0],
                break_time=latest_broken[1],
                confirmed_pivot_count=confirmed_pivot_count,
                candidate_count=len(candidates),
            )
        return TLTransitionResolution(
            state="NEW_ACTIVE",
            reason_code="NEW_N_STRUCTURE_CONFIRMED_AND_HL_BROKEN",
            active_candidate=active_candidate,
            broken_candidate=latest_broken[0],
            break_time=latest_broken[1],
            confirmed_pivot_count=confirmed_pivot_count,
            candidate_count=len(candidates),
        )

    if broken:
        return TLTransitionResolution(
            state="TRANSITION_NO_TL",
            reason_code="OLD_TL_BROKEN_NO_UNBROKEN_REPLACEMENT_N",
            active_candidate=None,
            broken_candidate=latest_broken[0],
            break_time=latest_broken[1],
            confirmed_pivot_count=confirmed_pivot_count,
            candidate_count=len(candidates),
        )

    return TLTransitionResolution(
        state="TRANSITION_NO_TL",
        reason_code="NO_ACTIVATED_N_STRUCTURE_YET",
        active_candidate=None,
        broken_candidate=None,
        break_time=None,
        confirmed_pivot_count=confirmed_pivot_count,
        candidate_count=len(candidates),
    )


def resolve_tl_transition_state(
    bars,
    symbol: str,
    timeframe: str,
    selected_state: dict | None = None,
    candidate_anchor_floor: datetime | None = None,
) -> TLTransitionResolution:
    """Resolve ACTIVE -> TRANSITION_NO_TL -> NEW_ACTIVE after normal selection.

    This layer does not invent TL geometry.  A NEW_ACTIVE TL is allowed only
    when the existing N-structure rules already produce an unbroken activated
    ChannelCandidate: two same-side confirmed pivots, the intervening decision
    HL, and a closed-bar HL break.

    TRANSITION_NO_TL means an older activated TL has broken and no replacement
    N has yet satisfied those existing activation rules.
    """
    turns = detect_turns(bars)
    candidates = build_channel_candidates(bars, turns.pivots)
    return resolve_tl_transition_from_candidates(
        bars,
        symbol,
        timeframe,
        candidates,
        len(turns.pivots),
        selected_state,
        candidate_anchor_floor,
    )
