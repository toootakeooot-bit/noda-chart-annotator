@echo off
setlocal
cd /d "%~dp0.."
echo NVT6 CLUSTER / SELECTOR BETA RESEARCH
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt6_cluster_selector_research.ps1"
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" (
  echo NVT6 CLUSTER / SELECTOR BETA RESEARCH FAILED exit=%EXITCODE%
) else (
  echo NVT6 CLUSTER / SELECTOR BETA RESEARCH COMPLETE
)
pause
exit /b %EXITCODE%
