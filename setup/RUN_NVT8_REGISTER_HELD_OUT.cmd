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

echo.
echo STRICT NVT8 ATTESTATION
echo Confirm BOTH are true:
echo   1. This video itself has not been watched/inspected for NVT.
echo   2. No related PDF, screenshots, transcript, subtitle, or same-source teacher material has been inspected for NVT.
echo.
set /p "ATTEST=Type YES to confirm, anything else to abort: "
if /i not "%ATTEST%"=="YES" (
  echo Registration aborted. Source was NOT marked clean held-out.
  pause
  exit /b 2
)

powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt8_register_held_out.ps1" -VideoPath "%VIDEO%" -AttestUnseen
set ERR=%ERRORLEVEL%

echo.
if not "%ERR%"=="0" (
  echo NVT8 HELD-OUT REGISTRATION FAILED ^(exit %ERR%^)
) else (
  echo NVT8 HELD-OUT REGISTRATION COMPLETE
)
pause
exit /b %ERR%
