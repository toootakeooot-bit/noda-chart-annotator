@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt9_usdjpy_mt4_smoke.ps1"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo NVT9 USDJPY AUTOMATED SIDE PASS - continue with MT4 renderer D1/H4/H1/M15.
) else if "%RC%"=="2" (
  echo NVT9 USDJPY WAITING FOR MT4 EXPORT - run NCA_NormalRun_Exporter on USDJPY# once, then rerun this file.
) else (
  echo NVT9 USDJPY SMOKE PRECHECK FAILED - exit=%RC%
)
echo.
pause
exit /b %RC%
