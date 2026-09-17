@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

set "VIDEO=%~1"
if "%VIDEO%"=="" (
  echo Drag a previously unseen USDJPY teacher video onto this CMD,
  echo or paste its full path below.
  echo.
  set /p "VIDEO=Video path: "
)

if "%VIDEO%"=="" (
  echo ERROR: no video path supplied.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt8_register_held_out.ps1" -VideoPath "%VIDEO%"
set ERR=%ERRORLEVEL%

echo.
if not "%ERR%"=="0" (
  echo NVT8 HELD-OUT REGISTRATION FAILED ^(exit %ERR%^)
) else (
  echo NVT8 HELD-OUT REGISTRATION COMPLETE
)
pause
exit /b %ERR%
