@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt9_0905_exact_transition.ps1"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo 09/05 EXACT TRANSITION REPLAY PASS
) else (
  echo 09/05 EXACT TRANSITION REPLAY BLOCKED/FAILED - exit=%RC%
)
echo.
pause
exit /b %RC%
