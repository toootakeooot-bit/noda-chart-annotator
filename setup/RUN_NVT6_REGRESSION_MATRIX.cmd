@echo off
setlocal
cd /d "%~dp0.."
echo NVT6 SOFT REGRESSION MATRIX
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup\run_nvt6_regression_matrix.ps1"
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" (
  echo NVT6 SOFT REGRESSION MATRIX FAILED exit=%EXITCODE%
) else (
  echo NVT6 SOFT REGRESSION MATRIX COMPLETE
)
pause
exit /b %EXITCODE%
