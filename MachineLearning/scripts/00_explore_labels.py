"""
00_explore_labels.py
第 0 步：看「答案」長什麼樣子

目的：在做任何模型之前，先搞清楚
  1. r4.2 裡有幾個內鬼、各屬於哪種情境
  2. 每個內鬼「做壞事」持續多久
  3. 內鬼們是在哪幾個月開始做壞事的（決定訓練／測試怎麼切）

執行方式：在 MachineLearning 資料夾裡打開終端機，輸入
  python scripts/00_explore_labels.py
"""
from pathlib import Path

import pandas as pd

# 路徑以「這支程式所在的位置」為準，從哪裡執行都找得到檔案
# scripts → MachineLearning → 專案根目錄
ROOT = Path(__file__).resolve().parents[2]
INSIDERS_CSV = ROOT / 'archive' / 'answers' / 'insiders.csv'

# ── 1. 讀答案檔 ───────────────────────────────────────────
ins = pd.read_csv(INSIDERS_CSV)

# 這個檔案收了 CERT 所有版本的內鬼，我們只要 r4.2 的
ins = ins[ins['dataset'].astype(str) == '4.2'].copy()

# start / end 原本是文字，轉成日期時間才能相減
ins['start'] = pd.to_datetime(ins['start'])
ins['end'] = pd.to_datetime(ins['end'])

# 每個內鬼做壞事持續幾天（end - start）
ins['duration_days'] = (ins['end'] - ins['start']).dt.days

print('=' * 50)
print('r4.2 內鬼人數：', ins['user'].nunique())
print('=' * 50)

# ── 2. 各情境：有幾人？做壞事持續多久？ ───────────────────
print('\n【各情境的人數與持續天數】')
summary = ins.groupby('scenario')['duration_days'].agg(
    人數='count', 最短天數='min', 中位數天數='median', 最長天數='max'
)
print(summary)

# ── 3. 每個月有幾人「開始」做壞事 ─────────────────────────
print('\n【每月開始做壞事的人數】')
by_month = ins.groupby(ins['start'].dt.to_period('M'))['user'].count()
print(by_month.to_string())

# ── 4. 如果用 2010 年訓練、2011 年測試，各有幾個內鬼？ ─────
cut = pd.Timestamp('2011-01-01')
n_train = (ins['start'] < cut).sum()
n_test = (ins['start'] >= cut).sum()
print('\n【假設在 2011-01-01 切一刀】')
print(f'訓練期（2010 年）開始犯案的內鬼：{n_train} 人')
print(f'測試期（2011 年）開始犯案的內鬼：{n_test} 人')

# ── 5. 如果「每一天」都算一列，標成 1 的天數大概有多少？ ──
total_bad_days = ins['duration_days'].clip(lower=1).sum()
print('\n【粗估：標成 1 的「人×天」列數】')
print(f'所有內鬼做壞事的天數加總：約 {total_bad_days} 天')
print(f'佔全部約 33 萬列的比例：約 {total_bad_days / 330000:.2%}')
