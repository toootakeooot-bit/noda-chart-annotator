@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt8h_usdjpy_historical_review.ps1"
set "ERR=%ERRORLEVEL%"
echo.
if not "%ERR%"=="0" (
  echo NVT8-H USDJPY HISTORICAL REVIEW FAILED ^(exit %ERR%^)
) else (
  echo NVT8-H USDJPY HISTORICAL REVIEW COMPLETE
)
pause
exit /b %ERR%
