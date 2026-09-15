@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt5_export_review_bundle.ps1"
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" (
  echo NVT5 REVIEW BUNDLE PASS
) else (
  echo NVT5 REVIEW BUNDLE FAILED exit=%RC%
)

echo.
pause
exit /b %RC%
