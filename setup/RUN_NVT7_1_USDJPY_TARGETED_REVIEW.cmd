@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt7_1_usdjpy_targeted_review.ps1"
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" (
  echo NVT7.1 USDJPY TARGETED REVIEW FAILED ^(exit %ERR%^)
) else (
  echo NVT7.1 USDJPY TARGETED REVIEW + B02_03 IMPORTANCE COMPLETE
)
pause
exit /b %ERR%
