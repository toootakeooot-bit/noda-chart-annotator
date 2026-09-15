@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt6_gt0006_visual_finalists.ps1"
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" (
  echo NVT6 GT0006 VISUAL FINALISTS FAILED exit=%ERR%
) else (
  echo NVT6 GT0006 VISUAL FINALISTS COMPLETE
)
pause
exit /b %ERR%
