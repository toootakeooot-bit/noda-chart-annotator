from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

LineRole = Literal["LARGE_DOW_TL", "TURN_LINE"]
VisibilityState = Literal["DRAW", "VALID_SUPPRESSED"]
BreakDirection = Literal["ABOVE", "BELOW"]
HighConfirmationState = Literal[
    "SWING_HIGH_CANDIDATE",
    "STRUCTURAL_HIGH_PARTIAL",
    "STRUCTURAL_HIGH_CONFIRMED_STRONG",
]
HierarchyState = Literal[
    "NO_LOCAL_BREAK",
    "SMALL_DOW_RISING_PARENT_NOT_PROMOTED",
    "LARGE_DOW_PROMOTED",
]


@dataclass(frozen=True)
class StructuralHighEvidence:
    retrace_38_confirmed: bool
    protected_low_broken: bool

    @property
    def state(self) -> HighConfirmationState:
        if self.retrace_38_confirmed and self.protected_low_broken:
            return "STRUCTURAL_HIGH_CONFIRMED_STRONG"
        if self.retrace_38_confirmed or self.protected_low_broken:
            return "STRUCTURAL_HIGH_PARTIAL"
        return "SWING_HIGH_CANDIDATE"

    def to_dict(self) -> dict:
        return {**asdict(self), "state": self.state}


@dataclass(frozen=True)
class DowHierarchyResult:
    small_dow_rising: bool
    large_dow_promoted: bool
    state: HierarchyState
    next_major_resistance: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def default_visibility(line_role: LineRole) -> VisibilityState:
    """Research-only default visibility.

    TURN_LINE is technically valid but suppressed from automatic chart rendering.
    LARGE_DOW_TL is the primary structural TL and is drawable by default.

    This module is not imported by Production Normal Run.
    """
    if line_role == "TURN_LINE":
        return "VALID_SUPPRESSED"
    if line_role == "LARGE_DOW_TL":
        return "DRAW"
    raise ValueError(f"unsupported line_role: {line_role}")


def closed_bar_break_confirmed(
    *,
    close: float,
    level: float,
    direction: BreakDirection,
) -> bool:
    """Research-only structural break rule fixed by user adjudication.

    A high/gate break is confirmed only when a later CLOSED BAR closes above
    the level. A protected-low break is confirmed only when a later CLOSED BAR
    closes below the level. Wick-only penetration does not count.
    """
    if direction == "ABOVE":
        return close > level
    if direction == "BELOW":
        return close < level
    raise ValueError(f"unsupported direction: {direction}")


def evaluate_rising_hierarchy(
    *,
    small_dow_high_broken: bool,
    active_large_dow_high_broken: bool,
) -> DowHierarchyResult:
    """Evaluate the user-semantic Dow hierarchy without changing line role.

    The boolean break inputs are expected to be produced by the closed-bar
    break rule in research code. Breaking a local/small-Dow high can set
    SMALL_DOW_RISING, but the parent large-Dow structure is not promoted until
    the active large-Dow high gate is also broken.
    """
    if active_large_dow_high_broken:
        return DowHierarchyResult(
            small_dow_rising=True,
            large_dow_promoted=True,
            state="LARGE_DOW_PROMOTED",
            next_major_resistance=None,
        )
    if small_dow_high_broken:
        return DowHierarchyResult(
            small_dow_rising=True,
            large_dow_promoted=False,
            state="SMALL_DOW_RISING_PARENT_NOT_PROMOTED",
            next_major_resistance="ACTIVE_LARGE_DOW_HIGH",
        )
    return DowHierarchyResult(
        small_dow_rising=False,
        large_dow_promoted=False,
        state="NO_LOCAL_BREAK",
        next_major_resistance="ACTIVE_LARGE_DOW_HIGH",
    )


def turn_line_role_after_small_dow_break() -> dict:
    """Return the invariant line-role contract after a local breakout."""
    return {
        "line_role": "TURN_LINE",
        "visibility": default_visibility("TURN_LINE"),
        "promoted_to_major_line": False,
        "automatic_display": False,
        "automatic_display_exception": None,
        "note": "Local breakout changes Dow hierarchy state, not TURN_LINE role.",
    }
