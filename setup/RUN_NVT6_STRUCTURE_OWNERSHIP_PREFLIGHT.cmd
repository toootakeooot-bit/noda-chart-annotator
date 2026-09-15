@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt6_structure_ownership_preflight.ps1"
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" (
  echo NVT6 STRUCTURE OWNERSHIP PREFLIGHT FAILED exit=%EXITCODE%
) else (
  echo NVT6 STRUCTURE OWNERSHIP PREFLIGHT COMPLETE
)
pause
exit /b %EXITCODE%
