@echo off
setlocal
cd /d "%~dp0"
python tools\run_pdf_only_once.py --live-root "." %*
endlocal
