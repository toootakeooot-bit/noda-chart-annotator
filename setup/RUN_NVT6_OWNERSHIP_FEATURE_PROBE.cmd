@echo off
setlocal
cd /d "%~dp0.."
echo NVT6 OWNERSHIP FEATURE PROBE
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt6_ownership_feature_probe.ps1"
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" (
  echo NVT6 OWNERSHIP FEATURE PROBE FAILED exit=%EXITCODE%
) else (
  echo NVT6 OWNERSHIP FEATURE PROBE COMPLETE
)
pause
exit /b %EXITCODE%
