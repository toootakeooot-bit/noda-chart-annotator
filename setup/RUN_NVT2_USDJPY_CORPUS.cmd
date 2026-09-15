@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt2_usdjpy_corpus.ps1"
set code=%ERRORLEVEL%
echo.
if not "%code%"=="0" (
  echo NVT2 USDJPY CORPUS FAILED exit=%code%
) else (
  echo NVT2 USDJPY CORPUS PASS
)
pause
exit /b %code%
