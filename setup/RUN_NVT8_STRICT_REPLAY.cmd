@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt8_strict_replay.ps1" -BrokerSymbol "USDJPY#"
set ERR=%ERRORLEVEL%
echo.
if "%ERR%"=="0" (
  echo NVT8 STRICT REPLAY BUNDLE READY
) else (
  echo NVT8 STRICT REPLAY NOT READY ^(exit %ERR%^)
)
pause
exit /b %ERR%
