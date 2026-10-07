"""
03_labels.py
第 3 步：標出每人每天的「答案」

規則：內鬼「第一次犯案前 N 天」～「最後一次犯案」標為 1，其餘為 0
  → 讓模型學的是「快要出事」，不只是「正在出事」，對應本專題「提早預警」的主軸
  N 一次產出 7／14／30 三種（label_7d、label_14d、label_30d），步驟 ④ 比較哪種提早最多

輸入：output/features.parquet（只取 user_id、date，確保跟特徵表一列對一列）
      archive/answers/insiders.csv
輸出：output/labels.parquet

執行方式（在 MachineLearning 資料夾裡）：
  python scripts/03_labels.py
"""
from pathlib import Path

import pandas as pd

# ── 設定 ──────────────────────────────────────────────────
BASE = Path(__file__).resolve().parents[1]     # MachineLearning
ANS = BASE.parent / 'archive' / 'answers' / 'insiders.csv'
OUT = BASE / 'output'

PRE_DAYS_LIST = [7, 14, 30]   # 第一次犯案前幾天開始標 1，三種都做
MAX_PRE = max(PRE_DAYS_LIST)

# phase：這一天在內鬼時間軸上的位置（步驟 ④ 評估與排除用）
NORMAL, PRE, DURING, AFTER = 'normal', 'pre', 'during', 'after'


if __name__ == '__main__':
    days = pd.read_parquet(OUT / 'features.parquet', columns=['user_id', 'date'])

    ins = pd.read_csv(ANS)
    ins = ins[ins['dataset'].astype(str) == '4.2'].copy()
    # 只取日期（不要時分秒）：特徵是以「天」為單位
    ins['first_mal'] = pd.to_datetime(ins['start']).dt.normalize()
    ins['last_mal'] = pd.to_datetime(ins['end']).dt.normalize()
    ins = ins.rename(columns={'user': 'user_id'})[['user_id', 'scenario', 'first_mal', 'last_mal']]

    df = days.merge(ins, on='user_id', how='left')
    df['is_insider'] = df['scenario'].notna().astype(int)

    # 距離第一次犯案幾天（負數＝還沒犯案）：步驟 ④ 算「提早幾天」用
    df['days_from_first'] = (df['date'] - df['first_mal']).dt.days

    pre_start = df['first_mal'] - pd.Timedelta(days=MAX_PRE)   # phase 的 pre 以最長的 30 天為準
    df['phase'] = NORMAL
    df.loc[(df['date'] >= pre_start) & (df['date'] < df['first_mal']), 'phase'] = PRE
    df.loc[(df['date'] >= df['first_mal']) & (df['date'] <= df['last_mal']), 'phase'] = DURING
    df.loc[df['date'] > df['last_mal'], 'phase'] = AFTER

    label_cols = []
    for n in PRE_DAYS_LIST:
        col = f'label_{n}d'
        in_pre = (df['days_from_first'] >= -n) & (df['days_from_first'] < 0)
        df[col] = ((df['phase'] == DURING) | in_pre).astype(int)
        label_cols.append(col)

    df = df[['user_id', 'date'] + label_cols + ['phase', 'is_insider', 'scenario',
             'first_mal', 'last_mal', 'days_from_first']]
    df.to_parquet(OUT / 'labels.parquet', index=False)

    # ── 檢查 ──
    print(f'列數 {len(df):,}（應與 features.parquet 相同）｜重複人天 {df.duplicated(["user_id", "date"]).sum()}')
    print(f'內鬼人數 {df.loc[df.is_insider == 1, "user_id"].nunique()}')
    for col in label_cols:
        print(f'{col} 標為 1 的列 {df[col].sum():,}（{df[col].mean():.2%}）')
    print('\n各階段列數：')
    print(df['phase'].value_counts().to_string())
    print('\n各情境：每人平均天數（pre 為 30 天窗）')
    s = (df[df.is_insider == 1]
         .groupby(['scenario', 'user_id'])['phase'].value_counts().unstack(fill_value=0)
         .groupby('scenario')[[PRE, DURING]].mean().round(1))
    print(s.to_string())
    no_row = set(ins['user_id']) - set(df.loc[df.label_7d == 1, 'user_id'])
    print(f'\n7 天窗下沒有任何一天被標 1 的內鬼：{len(no_row)} 人 {sorted(no_row)}')
