@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt8_strict_heldout_comparison.ps1"
set ERR=%ERRORLEVEL%
echo.
if "%ERR%"=="0" (
  echo NVT8 STRICT HELD-OUT COMPARISON PASS
) else if "%ERR%"=="4" (
  echo NVT8 STRICT HELD-OUT COMPARISON FAIL - upload the report unchanged.
) else (
  echo NVT8 STRICT HELD-OUT COMPARISON RUNNER ERROR ^(exit %ERR%^)
)
pause
exit /b %ERR%
