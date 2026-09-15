@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt5_gt0006_micro_dow_prototype.ps1"
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" (
  echo NVT5 GT_0006 MICRO-DOW PROTOTYPE FAILED exit=%EXITCODE%
) else (
  echo NVT5 GT_0006 MICRO-DOW PROTOTYPE COMPLETE
)
pause
exit /b %EXITCODE%
