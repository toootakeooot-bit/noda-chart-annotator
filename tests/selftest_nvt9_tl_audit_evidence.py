from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "nvt"))

from live_draw.model import ChannelCandidate, Pivot


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("nvt9_tl_audit_evidence", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def pivot(kind: str, idx: int, time: str, price: float, confirmed: str) -> Pivot:
    return Pivot(
        kind=kind,
        bar_index=idx,
        time=datetime.fromisoformat(time),
        price=price,
        confirmed_by_index=idx + 1,
        confirmed_by_time=datetime.fromisoformat(confirmed),
        retracement=0.38,
    )


def main() -> int:
    mod = load_module(ROOT / "tools" / "nvt" / "build_nvt9_tl_audit_evidence.py")

    a1 = pivot("HIGH", 10, "2026-07-01T00:00:00", 160.0, "2026-07-01T04:00:00")
    hl = pivot("LOW", 20, "2026-07-15T00:00:00", 155.0, "2026-07-15T04:00:00")
    a2 = pivot("HIGH", 30, "2026-08-01T00:00:00", 158.0, "2026-08-01T04:00:00")

    c = ChannelCandidate(
        direction="FALLING",
        anchor1=a1,
        anchor2=a2,
        slope_per_second=-7.467144563918757e-07,
        turn_span=3,
        tl_contacts=4,
        ch_contacts=5,
        unbroken_close=True,
        ch_anchor=hl,
        ch_offset=-4.0,
        zone_width=0.25,
        decision_hl=hl,
        hl_break_time=datetime.fromisoformat("2026-08-02T04:00:00"),
        hl_break_mode="CLOSED_BAR_CLOSE_PROVISIONAL",
    )

    line = {
        "line_id": "NCA_USDJPY#_H4_MID_DOW_G003",
        "symbol": "USDJPY#",
        "timeframe": "H4",
        "structure_level": "MID_DOW",
        "direction": "FALLING",
        "anchor1_time": "2026-07-01T00:00:00",
        "anchor1_price": 160.0,
        "anchor2_time": "2026-08-01T00:00:00",
        "anchor2_price": 158.0,
        "ch_offset": -4.0,
        "zone_width": 0.25,
        "status": "ACTIVE",
        "decision_hl_time": "2026-07-15T00:00:00",
        "decision_hl_price": 155.0,
        "decision_hl_kind": "LOW",
        "hl_break_time": "2026-08-02T04:00:00",
        "hl_break_mode": "CLOSED_BAR_CLOSE_PROVISIONAL",
    }

    assert mod.same_state_geometry(line, c)
    cd = mod.candidate_dict(c)
    assert cd["candidate_id"].startswith("FALLING:")
    assert cd["anchor1"]["retracement"] == 0.38
    assert cd["anchor2"]["closed_bar_confirmed"] is True
    assert cd["decision_hl"]["kind"] == "LOW"
    assert cd["break_by_close"] is True
    assert cd["turn_span"] == 3
    assert cd["tl_contacts"] == 4
    assert cd["ch_contacts"] == 5
    assert cd["unbroken_close"] is True

    selector = {
        "candidate_present": True,
        "direct_selected_candidate_id": c.id_key,
        "selector_match": True,
        "reason": {
            "turn_span": 3,
            "ch_contacts": 5,
            "tl_contacts": 4,
            "unbroken_close": True,
        },
        "selection_scope": "FULL_HISTORY_DIRECT_SELECTOR",
    }
    audit_record = mod.audit_record_from_match(
        line=line,
        role="CURRENT",
        candidate=c,
        level="MID_DOW",
        selector=selector,
    )

    assert audit_record["anchor1"]["retracement"] == 0.38
    assert audit_record["structure"]["hl_exists"] is True
    assert audit_record["structure"]["n_pattern_confirmed"] is True
    assert audit_record["structure"]["dow_confirmed"] is True
    assert audit_record["structure"]["hl_break"] is True
    assert audit_record["structure"]["break_by_close"] is True

    audit = mod.audit_line(audit_record)
    assert audit["Quality"] == "GOOD", audit
    assert audit["AuditReadiness"] == "READY", audit
    assert audit["missing_evidence"] == []
    assert audit["checks"]["Pivot"] == "PASS"
    assert audit["checks"]["Structure"] == "PASS"
    assert audit["checks"]["HL Break"] == "PASS"
    assert "P07" in audit["matched_patterns"]

    # Geometry mismatch must not be silently joined.
    wrong = dict(line)
    wrong["anchor2_price"] = 157.5
    assert not mod.same_state_geometry(wrong, c)

    # Previous/history rows are allowed to differ from the final direct selector.
    prev_selector = dict(selector)
    prev_selector["selector_match"] = None
    previous = mod.audit_record_from_match(
        line=line,
        role="PREVIOUS",
        candidate=c,
        level="MID_DOW",
        selector=prev_selector,
    )
    prev_audit = mod.audit_line(previous)
    assert prev_audit["Quality"] == "GOOD", prev_audit
    assert prev_audit["AuditReadiness"] == "READY"

    # Wick-only / non-closed activation must not be promoted as confirmed.
    c_wick = ChannelCandidate(
        direction=c.direction,
        anchor1=c.anchor1,
        anchor2=c.anchor2,
        slope_per_second=c.slope_per_second,
        turn_span=c.turn_span,
        tl_contacts=c.tl_contacts,
        ch_contacts=c.ch_contacts,
        unbroken_close=c.unbroken_close,
        ch_anchor=c.ch_anchor,
        ch_offset=c.ch_offset,
        zone_width=c.zone_width,
        decision_hl=c.decision_hl,
        hl_break_time=c.hl_break_time,
        hl_break_mode="WICK_ONLY",
    )
    wick_cd = mod.candidate_dict(c_wick)
    assert wick_cd["break_by_close"] is False
    wick_record = mod.audit_record_from_match(
        line=line,
        role="CURRENT",
        candidate=c_wick,
        level="MID_DOW",
        selector=selector,
    )
    wick_audit = mod.audit_line(wick_record)
    assert wick_audit["Quality"] == "HOLD", wick_audit
    assert wick_audit["checks"]["HL Break"] == "HOLD"

    print("NVT9 TL AUDIT EVIDENCE SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
