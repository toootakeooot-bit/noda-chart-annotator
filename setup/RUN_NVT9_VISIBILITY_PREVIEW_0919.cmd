@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt9_visibility_preview_0919.ps1"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo NVT9 09-19 VISIBILITY PREVIEW PASS
) else (
  echo NVT9 09-19 VISIBILITY PREVIEW FAILED - exit=%RC%
)
echo.
pause
exit /b %RC%
