@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nr7_symbol.ps1" -Symbol "JP225Cash#" -TestId "NR7-4"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo NR7-4 JP225Cash# AUTOMATED CHECK PASS
) else if "%RC%"=="2" (
  echo NR7-4 WAITING FOR JP225Cash# MT4 EXPORT - run NCA_NormalRun_Exporter on JP225Cash# first.
) else (
  echo NR7-4 JP225Cash# FAILED - exit=%RC%
)
echo.
pause
exit /b %RC%
