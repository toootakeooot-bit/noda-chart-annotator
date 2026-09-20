@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_nvt9_tfmap_preview_auto.ps1"
set EC=%ERRORLEVEL%
echo.
if not "%EC%"=="0" echo FAILED - exit=%EC%
pause
exit /b %EC%
