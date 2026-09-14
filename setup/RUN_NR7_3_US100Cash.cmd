@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nr7_symbol.ps1" -Symbol "US100Cash#" -TestId "NR7-3"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo NR7-3 US100Cash# AUTOMATED CHECK PASS
) else if "%RC%"=="2" (
  echo NR7-3 WAITING FOR US100Cash# MT4 EXPORT - run NCA_NormalRun_Exporter on US100Cash# first.
) else (
  echo NR7-3 US100Cash# FAILED - exit=%RC%
)
echo.
pause
exit /b %RC%
