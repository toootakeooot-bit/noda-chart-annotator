@echo off
setlocal

set "ROOT=%~dp0.."
set "OUT=%APPDATA%\MetaQuotes\Terminal\Common\Files\noda_draw\nvt_output"
set "BUNDLE=%OUT%\NVT5_REVIEW_BUNDLE_USDJPY.json"
set "HYP=%ROOT%\nvt\cases\NVT5_VISUAL_ANCHOR_HYPOTHESES_20260915.json"
set "RESULT=%OUT%\NVT5_TEACHER_ANCHOR_PROBE_USDJPY.json"

echo NVT5 TEACHER ANCHOR WINDOW PROBE START
echo Review bundle: %BUNDLE%
echo Hypotheses:    %HYP%
echo Output:        %RESULT%
echo.

python "%ROOT%\tools\nvt\probe_teacher_anchor_windows.py" --review-bundle "%BUNDLE%" --hypotheses "%HYP%" --output "%RESULT%"
if errorlevel 1 (
  echo.
  echo NVT5 TEACHER ANCHOR PROBE FAILED exit=%errorlevel%
  pause
  exit /b 1
)

echo.
echo NVT5 TEACHER ANCHOR PROBE PASS
echo Send this file for audit review:
echo %RESULT%
pause
exit /b 0
