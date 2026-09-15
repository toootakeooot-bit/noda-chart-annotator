@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt3_usdjpy_cases.ps1"
set code=%ERRORLEVEL%
echo.
if not "%code%"=="0" (
  echo NVT3 USDJPY CASES STOPPED exit=%code%
) else (
  echo NVT3 USDJPY CASES COMPLETE
)
pause
exit /b %code%
