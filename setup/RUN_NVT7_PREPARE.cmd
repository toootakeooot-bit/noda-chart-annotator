@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt7_prepare.ps1"
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" (
  echo NVT7 PREPARE FAILED ^(exit %ERR%^)
) else (
  echo NVT7 PREPARE COMPLETE
)
pause
exit /b %ERR%
