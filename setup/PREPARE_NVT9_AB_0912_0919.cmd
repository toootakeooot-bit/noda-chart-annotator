@echo off
setlocal
cd /d "%~dp0.."

echo NVT9 09/12 + 09/19 OLD/NEW A-B PREPARE
echo =======================================
echo [1/2] Build isolated OLD and NEW audit results
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_nvt9_ab_0912_0919.ps1"
if errorlevel 1 (
  echo A-B BUILD FAILED
  pause
  exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Install/compile MT4 A-B viewer
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_nvt9_tfmap_preview_auto.ps1"
if errorlevel 1 (
  echo MT4 INSTALL FAILED
  pause
  exit /b %ERRORLEVEL%
)

echo.
echo A-B PREPARE COMPLETE
echo.
echo MT4:
echo   Script: NCA_NVT9_AB_View
echo   Case:   2026-09-12 or 2026-09-19
echo   Variant: OLD or NEW
echo.
echo Colors are unchanged from the 09/19 approved display.
echo Use NCA_NVT9_Return_Live to return all four charts to live/current.
pause
exit /b 0
