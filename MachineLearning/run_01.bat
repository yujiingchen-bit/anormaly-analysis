@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist output mkdir output

echo === Checking packages ===
python -c "import duckdb, pandas" 2>nul || python -m pip install duckdb pandas

echo === Running 01_aggregate_daily.py (5 sources, http is the slowest) ===
powershell -NoProfile -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; python scripts/01_aggregate_daily.py 2>&1 | Tee-Object -FilePath output/run_01_log.txt"

echo.
echo === Done. Log saved to output\run_01_log.txt ===
pause
