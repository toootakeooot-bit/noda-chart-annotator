@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt6_gt0003_candidate_identity_audit.ps1"
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" (
  echo NVT6 GT0003 CANDIDATE IDENTITY AUDIT FAILED exit=%EXITCODE%
) else (
  echo NVT6 GT0003 CANDIDATE IDENTITY AUDIT COMPLETE
)
pause
exit /b %EXITCODE%
