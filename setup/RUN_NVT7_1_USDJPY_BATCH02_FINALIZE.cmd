@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt7_1_usdjpy_batch02_finalize.ps1"
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" (
  echo NVT7.1 USDJPY BATCH02 FINALIZE FAILED ^(exit %ERR%^)
) else (
  echo NVT7.1 USDJPY BATCH02 FINALIZE COMPLETE
  echo Upload:
  echo %%APPDATA%%\MetaQuotes\Terminal\Common\Files\noda_draw\nvt_output\nvt7_1_batch02_final\NVT7_1_BATCH02_FINAL_HANDOFF.json
)
pause
exit /b %ERR%
