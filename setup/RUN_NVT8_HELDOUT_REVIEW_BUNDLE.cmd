@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt8_heldout_review_bundle.ps1" -SampleSeconds 10
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" (
  echo NVT8 HELD-OUT REVIEW BUNDLE FAILED ^(exit %ERR%^)
) else (
  echo NVT8 HELD-OUT REVIEW BUNDLE COMPLETE
)
pause
exit /b %ERR%
