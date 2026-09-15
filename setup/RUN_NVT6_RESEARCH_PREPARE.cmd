@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt6_research_prepare.ps1"
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" (
  echo NVT6 RESEARCH PREPARE FAILED exit=%EXITCODE%
) else (
  echo NVT6 RESEARCH PREPARE PASS
)
pause
exit /b %EXITCODE%
