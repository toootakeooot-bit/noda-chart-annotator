@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt8_event_zoom_bundle.ps1" -SampleSeconds 5
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" (
  echo NVT8 EVENT ZOOM BUNDLE FAILED ^(exit %ERR%^)
) else (
  echo NVT8 EVENT ZOOM BUNDLE COMPLETE
)
pause
exit /b %ERR%
