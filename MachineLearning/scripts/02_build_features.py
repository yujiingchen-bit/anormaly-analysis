"""
02_build_features.py
第 2 步：五張每日表合併成「人 × 天」寬表，計算 A～E 五層特徵

輸入：output/daily_*.parquet（步驟 1 產出）
      archive/r4.2/LDAP/*.csv（月快照）、archive/r4.2/psychometric.csv（OCEAN）
輸出：output/features.parquet       每人每天一列
      output/feature_layers.json    每個特徵屬於哪一層（步驟 4 組合比較組用）

防洩漏原則：每一列只能用「當天以前」就知道的資訊
  B 層：只用過去 7／30 天，不含當天（rolling 的 closed='left'）
  C 層：m 月的資料只用 m-1 月以前的 LDAP 快照

執行方式（在 MachineLearning 資料夾裡）：
  python scripts/02_build_features.py
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ── 設定 ──────────────────────────────────────────────────
BASE = Path(__file__).resolve().parents[1]     # MachineLearning
RAW = BASE.parent / 'archive' / 'r4.2'
OUT = BASE / 'output'

SOURCES = ['logon', 'device', 'file', 'email', 'http']

# B 層要算偏離量的欄位（挑有意義的，不是全部）
DEV_COLS = [
    'logon_cnt', 'ah_logon_cnt', 'first_logon_min', 'last_logoff_min', 'other_pc_logon_cnt',
    'usb_cnt', 'file_cnt',
    'email_cnt', 'ext_rcpt_cnt', 'attach_cnt',
    'http_cnt', 'n_domain', 'job_cnt', 'cloud_cnt',
]
WINDOWS = {'7d': ('7D', 3), '30d': ('30D', 10)}   # 視窗長度、至少要有幾天紀錄才算

OCEAN = ['O', 'C', 'E', 'A', 'N']

t0 = time.time()
def log(msg):
    print(f'[{time.time() - t0:5.0f}s] {msg}', flush=True)


# ── A 層：今日行為（五張表合併） ──────────────────────────
# 以 logon 為底：有登入才算有上班；其他四張表的紀錄都落在有登入的日子裡（已檢查）
def layer_a():
    df = pd.read_parquet(OUT / 'daily_logon.parquet')
    for name in SOURCES[1:]:
        df = df.merge(pd.read_parquet(OUT / f'daily_{name}.parquet'),
                      on=['user_id', 'date'], how='left')
    df['date'] = pd.to_datetime(df['date'])

    # 沒紀錄＝當天沒做，補 0；首次登入時間缺值保留（補 0 會變成「半夜 0 點上班」）
    a_cols = [c for c in df.columns if c not in ('user_id', 'date')]
    zero_cols = [c for c in a_cols if c != 'first_logon_min']
    df[zero_cols] = df[zero_cols].fillna(0)
    df['is_weekend'] = (df['date'].dt.dayofweek >= 5).astype(int)
    a_cols.append('is_weekend')
    return df.sort_values(['user_id', 'date']).reset_index(drop=True), a_cols


# ── B 層：跟自己過去比的偏離量 ────────────────────────────
# 偏離 =（今天 − 過去平均）／（過去標準差 + 1）
#   + 1：避免標準差為 0（例如平常從不插 USB）時除以 0 爆掉
#   closed='left'：視窗不含今天，只用過去
#   紀錄天數不足（新進或資料開頭）→ 0，視為「沒有偏離」
def layer_b(df):
    b_cols = []
    g = df.set_index('date').groupby('user_id')[DEV_COLS]
    for tag, (win, min_n) in WINDOWS.items():
        roll = g.rolling(win, closed='left', min_periods=min_n)
        mean = roll.mean().reset_index(drop=True)
        std = roll.std().reset_index(drop=True)
        for c in DEV_COLS:
            name = f'z{tag}_{c}'
            df[name] = ((df[c] - mean[c]) / (std[c] + 1)).fillna(0)
            b_cols.append(name)
        log(f'  B 層 {tag} 完成')
    return df, b_cols


# ── C 層：組織事件（LDAP 月快照） ─────────────────────────
# m 月的每一天，只看 m-1 月以前的快照：
#   上月離開 ＝ 在 m-2 月快照、但不在 m-1 月快照的人
# r4.2 期間內沒有人轉調、也沒有主管離職（主管欄位從不變動），所以不做「主管更換／主管離職」
# 「同主管下屬離開人數」與「同團隊」99% 相同（一個團隊一位主管），只留團隊
def layer_c(df):
    snaps = {f.stem: pd.read_csv(f).fillna('') for f in sorted((RAW / 'LDAP').glob('*.csv'))}
    months = sorted(snaps)

    # 每個月「上個月離開」的人，依部門／團隊／同主管計數
    rows = []
    for prev2, prev1, cur in zip(months, months[1:], months[2:]):
        a, b = snaps[prev2], snaps[prev1]
        left = a[~a['user_id'].isin(b['user_id'])]
        rows.append({'month': cur, 'left': left})

    # 本人的部門、團隊、主管：用 2009-12 快照（無人轉調，任一月都一樣）
    org = snaps[months[0]][['user_id', 'functional_unit', 'department', 'team', 'supervisor', 'role']]

    feats = []
    for r in rows:
        left = r['left']
        m = org.copy()
        m['month'] = r['month']
        m['company_left_1m'] = len(left)
        m['dept_left_1m'] = m.set_index(['functional_unit', 'department']).index.map(
            left.groupby(['functional_unit', 'department']).size()).fillna(0).values
        m['team_left_1m'] = m.set_index(['functional_unit', 'department', 'team']).index.map(
            left.groupby(['functional_unit', 'department', 'team']).size()).fillna(0).values
        feats.append(m)
    c = pd.concat(feats, ignore_index=True)

    # 過去 3 個月部門累計離開人數（組織持續動盪）
    c = c.sort_values(['user_id', 'month'])
    c['dept_left_3m'] = c.groupby('user_id')['dept_left_1m'].transform(
        lambda s: s.rolling(3, min_periods=1).sum())

    c_cols = ['company_left_1m', 'dept_left_1m', 'team_left_1m', 'dept_left_3m']
    df['month'] = df['date'].dt.strftime('%Y-%m')
    df = df.merge(c[['user_id', 'month'] + c_cols], on=['user_id', 'month'], how='left')
    df[c_cols] = df[c_cols].fillna(0)        # 2010-01 以前沒有足夠快照 → 0

    # 部門、職稱只留著給 SHAP／Power BI 顯示用，不當特徵
    df = df.merge(org[['user_id', 'role', 'department']], on='user_id', how='left')
    return df, c_cols


# ── D 層：人格 OCEAN ─────────────────────────────────────
def layer_d(df):
    p = pd.read_csv(RAW / 'psychometric.csv')[['user_id'] + OCEAN]
    df = df.merge(p, on='user_id', how='left')
    return df, OCEAN


# ── E 層：人格 × 動態狀態 ────────────────────────────────
# 人格先標準化（減平均、除標準差），讓交互項以 0 為中心
#   N（神經質）× 周遭離職：情緒不穩的人，遇到組織動盪是否反應更大
#   C（盡責性）× 上下班偏離：盡責的人突然晚到早退，是否更反常
def layer_e(df):
    z = {k: (df[k] - df[k].mean()) / df[k].std() for k in OCEAN}
    pairs = {
        'N_x_dept_left_1m':   z['N'] * df['dept_left_1m'],
        'N_x_team_left_1m':   z['N'] * df['team_left_1m'],
        'C_x_z30d_first_logon': z['C'] * df['z30d_first_logon_min'],
        'C_x_z30d_last_logoff': z['C'] * df['z30d_last_logoff_min'],
        'A_x_z30d_ext_rcpt':  z['A'] * df['z30d_ext_rcpt_cnt'],
    }
    for k, v in pairs.items():
        df[k] = v
    return df, list(pairs)


# ── 主程式 ────────────────────────────────────────────────
if __name__ == '__main__':
    log('A 層：合併五張每日表')
    df, a_cols = layer_a()
    log(f'  {len(df):,} 列｜{df.user_id.nunique()} 人')

    log('B 層：自身偏離（7 天／30 天）')
    df, b_cols = layer_b(df)

    log('C 層：組織事件（LDAP）')
    df, c_cols = layer_c(df)

    log('D 層：人格')
    df, d_cols = layer_d(df)

    log('E 層：交互項')
    df, e_cols = layer_e(df)

    layers = {'A': a_cols, 'B': b_cols, 'C': c_cols, 'D': d_cols, 'E': e_cols}
    df = df[['user_id', 'date', 'role', 'department'] + sum(layers.values(), [])]
    df.to_parquet(OUT / 'features.parquet', index=False)
    (OUT / 'feature_layers.json').write_text(json.dumps(layers, ensure_ascii=False, indent=2), encoding='utf-8')

    # ── 檢查 ──
    log('完成，檢查結果：')
    print(f'  列數 {len(df):,}｜人數 {df.user_id.nunique()}｜期間 {df.date.min():%Y-%m-%d} ~ {df.date.max():%Y-%m-%d}')
    print(f'  重複人天 {df.duplicated(["user_id", "date"]).sum()}')
    for k, cols in layers.items():
        print(f'  {k} 層 {len(cols):2d} 個特徵｜缺值比例最高 {df[cols].isna().mean().max():.4f}')
    print(f'  特徵總數 {sum(len(v) for v in layers.values())}')
