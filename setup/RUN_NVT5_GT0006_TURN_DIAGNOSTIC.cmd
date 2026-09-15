@echo off
setlocal
cd /d "%~dp0.."

set "REPLAY_ROOT=%APPDATA%\MetaQuotes\Terminal\Common\Files\noda_draw\nvt_output\nvt5_replay"
set "OUT=%APPDATA%\MetaQuotes\Terminal\Common\Files\noda_draw\nvt_output\GT_0006_TURN_RECALL_DIAGNOSTIC.json"

echo NVT5 GT_0006 TURN RECALL DIAGNOSTIC START
echo Replay root: %REPLAY_ROOT%
echo.

python tools\nvt\diagnose_gt0006_turn_recall.py ^
  --replay-root "%REPLAY_ROOT%" ^
  --source-id NVT_VIDEO_20260912 ^
  --timeframe H1 ^
  --window-start 2026-09-01T00:00:00 ^
  --window-end 2026-09-11T23:00:00 ^
  --anchor1-start 2026-09-01T00:00:00 ^
  --anchor1-end 2026-09-03T23:59:59 ^
  --anchor2-start 2026-09-04T00:00:00 ^
  --anchor2-end 2026-09-11T23:00:00 ^
  --output "%OUT%"

set code=%ERRORLEVEL%
echo.
if not "%code%"=="0" (
  echo NVT5 GT_0006 TURN DIAGNOSTIC FAILED exit=%code%
) else (
  echo NVT5 GT_0006 TURN DIAGNOSTIC PASS
  echo Output: %OUT%
  echo.
  echo This is READ-ONLY research. Production Normal Run and NCA_DRAW__ are untouched.
)
pause
exit /b %code%
