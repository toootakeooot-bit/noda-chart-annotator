@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt9_history_4w_0919.ps1"
set RC=%ERRORLEVEL%
echo.
if not "%RC%"=="0" echo FAILED - exit=%RC%
if "%RC%"=="0" echo COMPLETE
pause
exit /b %RC%
