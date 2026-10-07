@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist output mkdir output

echo === Checking packages ===
python -c "import duckdb, pandas, pyarrow" 2>nul || python -m pip install duckdb pandas pyarrow

echo === Running 03_labels.py ===
powershell -NoProfile -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; python scripts/03_labels.py 2>&1 | Tee-Object -FilePath output/run_03_log.txt"

echo.
echo === Done. Log saved to output\run_03_log.txt ===
pause
