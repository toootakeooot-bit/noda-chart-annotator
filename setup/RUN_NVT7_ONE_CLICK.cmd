@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt7_one_click.ps1"
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" (
  echo NVT7 ONE-CLICK FAILED ^(exit %ERR%^)
) else (
  echo NVT7 ONE-CLICK COMPLETE
)
pause
exit /b %ERR%
