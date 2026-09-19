@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt9_draw_rationale_usdjpy.ps1"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo NVT9 DRAW RATIONALE PASS
) else (
  echo NVT9 DRAW RATIONALE FAILED - exit=%RC%
)
echo.
pause
exit /b %RC%
