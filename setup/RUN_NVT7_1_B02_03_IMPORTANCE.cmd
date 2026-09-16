@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt7_1_b02_03_importance.ps1"
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" (
  echo NVT7.1 B02_03 LINE IMPORTANCE FAILED ^(exit %ERR%^)
) else (
  echo NVT7.1 B02_03 LINE IMPORTANCE COMPLETE
)
pause
exit /b %ERR%
