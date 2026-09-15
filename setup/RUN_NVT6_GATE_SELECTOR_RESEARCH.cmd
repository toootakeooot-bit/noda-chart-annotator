@echo off
setlocal
cd /d "%~dp0.."
echo NVT6 GATE + SELECTOR RESEARCH
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt6_gate_selector_research.ps1"
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" (
  echo NVT6 GATE + SELECTOR RESEARCH FAILED exit=%EXITCODE%
) else (
  echo NVT6 GATE + SELECTOR RESEARCH COMPLETE
)
pause
exit /b %EXITCODE%
