@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist output mkdir output

echo === Checking packages ===
python -c "import pandas, pyarrow, sklearn, xgboost, shap" 2>nul || python -m pip install pandas pyarrow scikit-learn xgboost shap

echo === Running 05_explain_export.py (about 10-15 min) ===
powershell -NoProfile -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; python scripts/05_explain_export.py 2>&1 | Tee-Object -FilePath output/run_05_log.txt"

echo.
echo === Done. Log saved to output\run_05_log.txt ===
pause
