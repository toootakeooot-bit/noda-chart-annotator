from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

history = (ROOT / "mt4" / "NCA_NVT9_History_View.mq4").read_text(encoding="utf-8")
live = (ROOT / "mt4" / "NCA_NVT9_Return_Live.mq4").read_text(encoding="utf-8")
ab = (ROOT / "mt4" / "NCA_NVT9_AB_View.mq4").read_text(encoding="utf-8")
installer = (ROOT / "setup" / "install_nvt9_tfmap_preview_auto.ps1").read_text(encoding="utf-8")
builder = (ROOT / "tools" / "nvt" / "build_nvt9_historical_4w.py").read_text(encoding="utf-8")

# History viewer must directly read isolated case files and never overwrite live preview.
assert "nvt9_history_4w_0919" in history
assert "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv" in history
assert "ChartSetInteger(chartId, CHART_AUTOSCROLL, false)" in history
assert "ChartNavigate(chartId, CHART_END, -shift)" in history
assert "iBarShift(symbol, period, cutoff, false)" in history
assert "ChartFirst()" in history and "ChartNext(chartId)" in history
assert "CopyFile" not in history and "FileMove" not in history
assert "CASE_20260822" in history
assert "CASE_20260829" in history
assert "CASE_20260905" in history
assert "CASE_20260912" in history
assert 'OBJ_VLINE' in history
assert 'NVT9_CASE_CUTOFF__' in history
assert 'CaseMarkerColor = clrWhite' in history
assert 'CaseMarkerWidth = 2' in history
assert 'DrawCaseMarker(chartId, cutoff)' in history

# A/B viewer must keep the 09/19 color policy and isolate OLD/NEW files.
assert "nvt9_ab_0912_0919" in ab
assert "VARIANT_OLD" in ab and "VARIANT_NEW" in ab
assert "CASE_20260912" in ab and "CASE_20260919" in ab
assert "D1TLColor = clrYellow" in ab
assert "H4TLColor = clrAqua" in ab
assert "H1TLColor = clrLime" in ab
assert "M15TLColor = clrMagenta" in ab
assert "ChartSetInteger(chartId, CHART_AUTOSCROLL, false)" in ab
assert "OBJ_VLINE" in ab

# Return-live must restore latest position + autoscroll and render the current live preview.
assert "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv" in live
assert "ChartNavigate(chartId, CHART_END, 0)" in live
assert "ChartSetInteger(chartId, CHART_AUTOSCROLL, true)" in live
assert "ChartFirst()" in live and "ChartNext(chartId)" in live

# Installer must deploy deep-history exporter plus the three audit scripts.
for name in (
    "NCA_NVT_HistoryExporter.mq4",
    "NCA_NVT9_TFMap_Preview_Renderer.mq4",
    "NCA_NVT9_History_View.mq4",
    "NCA_NVT9_AB_View.mq4",
    "NCA_NVT9_Return_Live.mq4",
):
    assert name in installer

# Historical builder must source NVT deep history and hard-filter before cutoff.
assert 'default="NVT"' in builder
assert 'input_name(args.symbol, tf, args.input_prefix)' in builder
assert "STOP_DEEP_HISTORY_REQUIRED" in builder
assert "bars = [b for b in all_bars if b.time < cutoff]" in builder
assert '"future_data_used": False' in builder
assert "PASS_4W_NO_FUTURE_LEAK" in builder

print("NVT9 HISTORY VIEW / RETURN LIVE SELFTEST PASS")
