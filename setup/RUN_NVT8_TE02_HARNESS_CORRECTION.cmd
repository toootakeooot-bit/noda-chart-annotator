@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt8_te02_harness_correction.ps1"
set ERR=%ERRORLEVEL%
echo.
if "%ERR%"=="0" (
  echo NVT8 HARNESS CORRECTION PASS
) else (
  echo NVT8 HARNESS CORRECTION FAILED ^(exit %ERR%^)
)
pause
exit /b %ERR%
