@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nr7_1_usdjpy.ps1"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo NR7-1 AUTOMATED CHECK PASS
) else if "%RC%"=="2" (
  echo NR7-1 WAITING FOR MT4 EXPORT - run NCA_NormalRun_Exporter on USDJPY# first.
) else (
  echo NR7-1 FAILED - exit=%RC%
)
echo.
pause
exit /b %RC%
