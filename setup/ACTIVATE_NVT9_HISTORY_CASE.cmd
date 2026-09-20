@echo off
setlocal
if "%~1"=="" (
  echo Usage: ACTIVATE_NVT9_HISTORY_CASE.cmd 20260822^|20260829^|20260905^|20260912
  exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0activate_nvt9_history_case.ps1" -Case "%~1"
set RC=%ERRORLEVEL%
pause
exit /b %RC%
