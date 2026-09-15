@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt6_preflight_all.ps1"
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" (
  echo NVT6 PREFLIGHT ALL FAILED exit=%EXITCODE%
) else (
  echo NVT6 PREFLIGHT ALL COMPLETE
)
pause
exit /b %EXITCODE%
