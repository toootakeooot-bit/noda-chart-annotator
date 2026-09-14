@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nr7_symbol.ps1" -Symbol "GOLD#" -TestId "NR7-2"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo NR7-2 GOLD# AUTOMATED CHECK PASS
) else if "%RC%"=="2" (
  echo NR7-2 WAITING FOR GOLD# MT4 EXPORT - run NCA_NormalRun_Exporter on GOLD# first.
) else (
  echo NR7-2 GOLD# FAILED - exit=%RC%
)
echo.
pause
exit /b %RC%
