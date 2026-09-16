@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt7_lifecycle_preflight.ps1"
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" (
  echo NVT7 LIFECYCLE PREFLIGHT FAILED ^(exit %ERR%^)
) else (
  echo NVT7 LIFECYCLE PREFLIGHT COMPLETE
)
pause
exit /b %ERR%
