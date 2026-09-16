@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt8_holdout_preflight.ps1"
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" (
  echo NVT8 HELD-OUT PREFLIGHT EXECUTION FAILED ^(exit %ERR%^)
) else (
  echo NVT8 HELD-OUT PREFLIGHT COMPLETE
)
pause
exit /b %ERR%
