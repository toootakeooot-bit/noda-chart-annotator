@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt5_usdjpy_replays.ps1"
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" (
  echo NVT5 USDJPY REPLAYS PASS
) else (
  echo NVT5 USDJPY REPLAYS FAILED exit=%RC%
)

echo.
pause
exit /b %RC%
