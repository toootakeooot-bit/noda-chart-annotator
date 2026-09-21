@echo off
setlocal
cd /d "%~dp0.."

echo NVT9 09/19 AUDIT REPLAY PREPARE
echo ===============================
echo Case:    2026-09-19
echo Variant: OLD - frozen 09/19 baseline
echo Audit:   ID10IQ200
echo.

echo [1/2] Rebuild historical A/B package and enforce exact 09/19 baseline gate
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt9_ab_0912_0919.ps1"
if errorlevel 1 (
  echo.
  echo STOP: 09/19 baseline replay did not pass. MT4 replay is blocked.
  pause
  exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Install/compile the MT4 audit viewer
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_nvt9_tfmap_preview_auto.ps1"
if errorlevel 1 (
  echo.
  echo STOP: MT4 audit viewer install failed.
  pause
  exit /b %ERRORLEVEL%
)

echo.
echo READY FOR 09/19 VISUAL CHECK
echo ----------------------------
echo Open USDJPY# D1/H4/H1/M15 charts.
echo Run script: NCA_NVT9_AB_View
echo Defaults on this audit branch are already:
echo   HistoryCase = CASE_20260919
echo   Variant     = VARIANT_OLD
echo.
echo Selector audit:
echo   %%APPDATA%%\MetaQuotes\Terminal\Common\Files\noda_draw\live_output\nvt9_ab_0912_0919\20260919\OLD\NVT9_SELECTOR_TRACE.json
echo.
echo The viewer uses the existing 09/19 color policy and draws a white cutoff marker.
echo Return to live charts with NCA_NVT9_Return_Live.
echo.
pause
exit /b 0
