@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt7_1_usdjpy_post_batch.ps1"
set "ERR=%ERRORLEVEL%"
echo.
if not "%ERR%"=="0" (
  echo NVT7.1 USDJPY POST-BATCH FAILED ^(exit %ERR%^)
) else (
  echo NVT7.1 USDJPY POST-BATCH PASS_CONTRACTS
)
pause
exit /b %ERR%
