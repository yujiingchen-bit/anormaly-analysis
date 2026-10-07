"""
04_train_eval.py
第 4 步：訓練與評估——比較「哪種做法能提早幾天預警」

實驗設計：
  4 組特徵 × 3 種模型 × 3 種標籤窗（7／14／30 天）＝ 36 組，另加「人格洗牌測試」
  逐月滾動（walk-forward）：用 m 月以前的資料訓練，考 m 月；考試月 2010/08～2011/05

評估方式（所有組別用同一把尺，才能公平比較）：
  每天依風險分數排出前 10 名＝發出警報
  只評「模型沒看過答案」的內鬼：第一次犯案日 ≥ 2010/08/31（犯案前 30 天都在考試期內）
  提早天數 ＝ 第一次犯案日 − 第一次進入前 10 名的日子（只看犯案前 30 天～最後一次犯案）
            正數＝在犯案前就預警；負數＝犯案開始後才發現

輸入：output/features.parquet、labels.parquet、feature_layers.json
輸出：output/results_summary.csv     每組實驗一列（主要成果）
      output/results_insiders.csv    每組 × 每個內鬼：有沒有抓到、提早幾天
      output/test_scores.parquet     每組實驗的每日風險分數（步驟 ⑤ 用）

執行方式（在 MachineLearning 資料夾裡）：
  python scripts/04_train_eval.py           → 全部 37 組（較久）
  python scripts/04_train_eval.py quick     → 只跑主模型 ④ × XGBoost × 30 天，先確認流程
"""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

warnings.filterwarnings('ignore')

# ── 設定 ──────────────────────────────────────────────────
BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'output'

TEST_MONTHS = pd.period_range('2010-08', '2011-05', freq='M')
TOP_K = 10                 # 每天調查人數
EVAL_PRE = 30              # 評估窗：犯案前 30 天起算（所有組別相同）
NEG_KEEP = 0.2             # 訓練時正常列只抽 20%（加權補回），加快速度
SEED = 42

GROUPS = {                 # 比較組（對應 method.md）
    'G1_A+B':         ['A', 'B'],
    'G2_A+B+D':       ['A', 'B', 'D'],
    'G3_A+B+C':       ['A', 'B', 'C'],
    'G4_A+B+C+D+E':   ['A', 'B', 'C', 'D', 'E'],
}
LABELS = ['label_7d', 'label_14d', 'label_30d']


def make_model(name):
    if name == 'LR':
        return make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=0.1))
    if name == 'RF':
        return RandomForestClassifier(n_estimators=200, min_samples_leaf=5, max_features='sqrt',
                                      n_jobs=-1, random_state=SEED)
    if name == 'XGB':
        return XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8,
                             colsample_bytree=0.8, tree_method='hist', n_jobs=-1, random_state=SEED,
                             verbosity=0)
    raise ValueError(name)


t0 = time.time()
def log(msg):
    print(f'[{time.time() - t0:6.0f}s] {msg}', flush=True)


# ── 讀資料 ────────────────────────────────────────────────
def load():
    f = pd.read_parquet(OUT / 'features.parquet')
    l = pd.read_parquet(OUT / 'labels.parquet')
    layers = json.loads((OUT / 'feature_layers.json').read_text(encoding='utf-8'))
    df = f.merge(l, on=['user_id', 'date'], how='inner')
    df = df[df['phase'] != 'after'].reset_index(drop=True)      # 犯案後到離職：不訓練也不評估
    # 首次登入缺值（跨夜）：以該人過去中位數補，LR 不接受缺值
    df['first_logon_min'] = df['first_logon_min'].fillna(
        df.groupby('user_id')['first_logon_min'].transform('median')).fillna(480)
    df['month'] = df['date'].dt.to_period('M')
    # 評估用「答案」：犯案前 30 天～犯案中（所有組別同一把尺）
    df['eval_pos'] = ((df['phase'] == 'during') |
                      ((df['days_from_first'] >= -EVAL_PRE) & (df['days_from_first'] < 0))).astype(int)
    return df, layers


# ── 訓練權重：每個內鬼權重相同，正負兩邊總權重相等 ─────────
def weights(y, users):
    w = np.ones(len(y), dtype=float)
    pos = y == 1
    if pos.sum() == 0:
        return w
    n_neg = (~pos).sum()
    per_user = pd.Series(users[pos]).map(pd.Series(users[pos]).value_counts()).values
    n_ins = pd.Series(users[pos]).nunique()
    w[pos] = n_neg / n_ins / per_user          # 每個內鬼合計 n_neg / n_ins
    return w


# ── 逐月滾動：回傳考試期每天每人的分數 ─────────────────────
def walk_forward(df, feats, label, model_name, shuffle_ocean=False):
    rng = np.random.default_rng(SEED)
    data = df
    if shuffle_ocean:                          # 人格洗牌：打亂「人 ↔ 人格分數」的對應
        users = df['user_id'].unique()
        perm = dict(zip(users, rng.permutation(users)))
        ocean = df.drop_duplicates('user_id').set_index('user_id')[['O', 'C', 'E', 'A', 'N']]
        shuffled = ocean.loc[[perm[u] for u in df['user_id']]].values
        data = df.copy()
        data[['O', 'C', 'E', 'A', 'N']] = shuffled
        # 交互項跟著重算
        z = {k: (data[k] - data[k].mean()) / data[k].std() for k in 'OCEAN'}
        data['N_x_dept_left_1m'] = z['N'] * data['dept_left_1m']
        data['N_x_team_left_1m'] = z['N'] * data['team_left_1m']
        data['C_x_z30d_first_logon'] = z['C'] * data['z30d_first_logon_min']
        data['C_x_z30d_last_logoff'] = z['C'] * data['z30d_last_logoff_min']
        data['A_x_z30d_ext_rcpt'] = z['A'] * data['z30d_ext_rcpt_cnt']

    out = []
    for m in TEST_MONTHS:
        cut = m.start_time
        train = data[data['date'] < cut]
        # 防洩漏 1：截止日時還沒犯案的內鬼，沒人知道他是內鬼 → 他的「1」不能進訓練
        unknown = train['first_mal'].notna() & (train['first_mal'] >= cut) & (train[label] == 1)
        train = train[~unknown]
        # 正常列抽樣（加權補回）
        neg = train[label] == 0
        keep = ~neg | (rng.random(len(train)) < NEG_KEEP)
        train = train[keep]
        y = train[label].values
        w = weights(y, train['user_id'].values)
        w[y == 0] /= NEG_KEEP

        test = data[data['month'] == m]
        # 防洩漏 2：考試只看「截止日前還沒被發現」的人（已知內鬼移出排名）
        test = test[~(test['first_mal'].notna() & (test['first_mal'] < cut))]

        model = make_model(model_name)
        if model_name == 'LR':
            model.fit(train[feats], y, logisticregression__sample_weight=w)
        else:
            model.fit(train[feats], y, sample_weight=w)
        s = test[['user_id', 'date', 'eval_pos', 'scenario', 'first_mal', 'last_mal', 'days_from_first']].copy()
        s['score'] = model.predict_proba(test[feats])[:, 1]
        out.append(s)
    return pd.concat(out, ignore_index=True)


# ── 評估 ──────────────────────────────────────────────────
def evaluate(s):
    s = s.copy()
    s['rank'] = s.groupby('date')['score'].rank(ascending=False, method='first')
    s['alert'] = s['rank'] <= TOP_K

    # 只評沒看過答案、且犯案前 30 天都在考試期內的內鬼
    first_ok = TEST_MONTHS[0].start_time + pd.Timedelta(days=EVAL_PRE)
    ev = s[s['first_mal'] >= first_ok]
    ins = ev.groupby('user_id').agg(scenario=('scenario', 'first'), first_mal=('first_mal', 'first'))
    hit = ev[ev['alert'] & (ev['eval_pos'] == 1)].groupby('user_id')['date'].min()
    ins['first_alert'] = hit
    ins['detected'] = ins['first_alert'].notna()
    ins['lead_days'] = (ins['first_mal'] - ins['first_alert']).dt.days

    # 每日命中率：抓到 ÷ 當天可抓上限
    s['hit'] = s['alert'] & (s['eval_pos'] == 1)
    day = s.groupby('date').agg(pos=('eval_pos', 'sum'), hit=('hit', 'sum'))
    day = day[day['pos'] > 0]
    p_at_k = (day['hit'] / day['pos'].clip(upper=TOP_K)).mean()

    # 背景列入率：內鬼在「評估窗之前」（犯案前 60～31 天）被列入前 10 名的比例
    #   高 → 這個人平常就常被列入，「提早」可能只是長期被盯，不是偵測到變化
    bg = ev[(ev['days_from_first'] >= -60) & (ev['days_from_first'] < -EVAL_PRE)]
    normal_rate = s.loc[s['first_mal'].isna(), 'alert'].mean()

    det = ins[ins['detected']]
    summ = {
        '評估內鬼數': len(ins),
        '抓到人數': int(ins['detected'].sum()),
        '抓到比例': ins['detected'].mean(),
        '提早天數_中位數': det['lead_days'].median(),
        '犯案前就預警人數': int((det['lead_days'] > 0).sum()),
        '提早_情境1': det.loc[det.scenario == 1, 'lead_days'].median(),
        '提早_情境2': det.loc[det.scenario == 2, 'lead_days'].median(),
        '提早_情境3': det.loc[det.scenario == 3, 'lead_days'].median(),
        '背景列入率_內鬼': bg['alert'].mean(),
        '背景列入率_一般員工': normal_rate,
        'Precision@10': p_at_k,
        'Recall_列': s.loc[s.eval_pos == 1, 'alert'].mean(),
        'Precision_列': s.loc[s.alert, 'eval_pos'].mean(),
        'PR_AUC': average_precision_score(s['eval_pos'], s['score']),
    }
    return summ, ins.reset_index()


# ── 主程式 ────────────────────────────────────────────────
if __name__ == '__main__':
    quick = 'quick' in sys.argv[1:]
    df, layers = load()
    log(f'資料 {len(df):,} 列（已排除 after）')

    runs = []
    if quick:
        runs.append(('G4_A+B+C+D+E', 'XGB', 'label_30d', False))
    else:
        for g in GROUPS:
            for m in ['LR', 'RF', 'XGB']:
                for lab in LABELS:
                    runs.append((g, m, lab, False))
        runs.append(('G4_A+B+C+D+E', 'XGB', 'label_14d', True))   # 人格洗牌測試

    summaries, insiders, scores = [], [], {}
    for i, (g, m, lab, shuf) in enumerate(runs, 1):
        feats = sum((layers[k] for k in GROUPS[g]), [])
        name = f'{g}|{m}|{lab}' + ('|人格洗牌' if shuf else '')
        s = walk_forward(df, feats, lab, m, shuffle_ocean=shuf)
        summ, ins = evaluate(s)
        summaries.append({'實驗': name, '特徵組': g, '模型': m, '標籤窗': lab, '人格洗牌': shuf, **summ})
        ins['實驗'] = name
        insiders.append(ins)
        scores[name] = s.set_index(['user_id', 'date'])['score']
        log(f'({i}/{len(runs)}) {name}｜抓到 {summ["抓到人數"]}/{summ["評估內鬼數"]}｜'
            f'提早中位數 {summ["提早天數_中位數"]}｜P@10 {summ["Precision@10"]:.3f}')

    res = pd.DataFrame(summaries).round(3)
    suffix = '_quick' if quick else ''
    res.to_csv(OUT / f'results_summary{suffix}.csv', index=False, encoding='utf-8-sig')
    pd.concat(insiders).to_csv(OUT / f'results_insiders{suffix}.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(scores).reset_index().to_parquet(OUT / f'test_scores{suffix}.parquet', index=False)

    log('完成。依「提早天數中位數」排序前 10 組：')
    cols = ['實驗', '抓到人數', '提早天數_中位數', '犯案前就預警人數', 'Precision@10', 'PR_AUC']
    print(res.sort_values(['提早天數_中位數', '抓到人數'], ascending=False)[cols].head(10).to_string(index=False))
