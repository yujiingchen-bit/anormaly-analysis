@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist output mkdir output

echo === Checking packages ===
python -c "import pandas, pyarrow, sklearn, xgboost" 2>nul || python -m pip install pandas pyarrow scikit-learn xgboost

echo === Running 04_train_eval.py (37 runs, about 30-60 min) ===
powershell -NoProfile -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; python scripts/04_train_eval.py 2>&1 | Tee-Object -FilePath output/run_04_log.txt"

echo.
echo === Done. Log saved to output\run_04_log.txt ===
pause
