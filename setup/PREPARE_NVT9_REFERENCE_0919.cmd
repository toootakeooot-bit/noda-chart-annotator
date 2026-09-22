@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt9_reference_0919.ps1"
set RC=%ERRORLEVEL%
echo.
if not "%RC%"=="0" echo FAILED - exit=%RC%
if "%RC%"=="0" echo COMPLETE - 09/19 reference restored and diagnostic generated.
pause
exit /b %RC%
