@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt9_phase1_advance_0919.ps1"
set EC=%ERRORLEVEL%
echo.
if not "%EC%"=="0" echo FAILED - exit=%EC%
pause
exit /b %EC%
