@echo off
setlocal
cd /d "%~dp0.."

echo NVT9 HISTORY AUDIT PREPARE
echo ==========================
echo [1/2] Build four no-lookahead historical cases
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt9_history_4w_0919.ps1"
if errorlevel 1 (
  echo HISTORY BUILD FAILED
  pause
  exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Install/compile MT4 history and return-live scripts
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_nvt9_tfmap_preview_auto.ps1"
if errorlevel 1 (
  echo MT4 INSTALL FAILED
  pause
  exit /b %ERRORLEVEL%
)

echo.
echo PREPARE COMPLETE
echo MT4 scripts:
echo   NCA_NVT9_History_View
echo   NCA_NVT9_Return_Live
echo.
echo History_View default case is 2026-09-12.
echo Run it once on any USDJPY# D1/H4/H1/M15 chart; it applies to all four open target charts.
echo Return_Live restores all four target charts to the latest bar and AutoScroll.
pause
exit /b 0
