@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nr7_1_renderer_failure_probe.ps1"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo NR7-1 RENDERER FAILURE PROBE HELPER PASS
) else (
  echo NR7-1 RENDERER FAILURE PROBE HELPER FAILED - exit=%RC%
)
echo.
pause
exit /b %RC%
