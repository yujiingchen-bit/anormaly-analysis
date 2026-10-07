"""
05_explain_export.py
第 5 步：用主模型產出每日風險名單，以 SHAP 說明「為什麼是他」，匯出給 Power BI

主模型：G1（只用行為）× Random Forest × 30 天標籤（理由見 method.md 第 6 節）
做法：與步驟 4 相同的逐月滾動（同樣的抽樣與亂數種子），每個月訓練一次，
      替該月每一天打分數；SHAP 只算每天前 10 名

輸入：output/features.parquet、labels.parquet、feature_layers.json
輸出（output/powerbi/）：
  top10_daily.csv       每天前 10 名＋前三大風險原因        → 首頁 Top 10
  risk_daily.csv        每人每天的風險分數與排名            → 個人風險走勢、部門熱力圖
  answer_key.csv        內鬼答案（情境、犯案期間）          → 只給「模型驗證」頁
  model_validation.csv  每個評估內鬼：第一次預警日、提早天數 → 只給「模型驗證」頁
另存 output/shap_top10.parquet：Top 10 每一筆的完整 SHAP 值與特徵值（步驟 6 畫圖用）

執行方式（在 MachineLearning 資料夾裡）：
  python scripts/05_explain_export.py
"""
import importlib.util
import time
from pathlib import Path

import numpy as np
import pandas as pd
import shap

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'output'
PBI = OUT / 'powerbi'
PBI.mkdir(exist_ok=True)

# 沿用步驟 4 的設定與函式，確保分數和第 5 節的結果一模一樣
spec = importlib.util.spec_from_file_location('step4', BASE / 'scripts' / '04_train_eval.py')
s4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s4)

LABEL = 'label_30d'
GROUP = 'G1_A+B'
SCENARIO_NAME = {1: '情境1 洩密', 2: '情境2 跳槽', 3: '情境3 報復'}

# ── 特徵中文名稱（給 Power BI 顯示） ──────────────────────
NAME = {
    'logon_cnt': '登入次數', 'ah_logon_cnt': '下班後登入次數', 'first_logon_min': '上班時間',
    'last_logoff_min': '下班時間', 'n_pc': '使用電腦台數', 'other_pc_logon_cnt': '登入他人電腦次數',
    'usb_cnt': 'USB 次數', 'ah_usb_cnt': '下班後 USB 次數', 'file_cnt': '複製到 USB 檔案數',
    'ah_file_cnt': '下班後複製檔案數', 'exe_file_cnt': '複製執行檔數', 'email_cnt': '寄信數',
    'ah_email_cnt': '下班後寄信數', 'ext_rcpt_cnt': '外部收件人數', 'max_rcpt_cnt': '單封最多收件人',
    'attach_cnt': '附件數', 'http_cnt': '瀏覽網頁數', 'ah_http_cnt': '下班後瀏覽數',
    'n_domain': '瀏覽網站數', 'leak_cnt': 'wikileaks 瀏覽', 'job_cnt': '求職網站瀏覽',
    'cloud_cnt': '雲端分享網站瀏覽', 'keylog_cnt': 'keylog 相關瀏覽', 'is_weekend': '週末上班',
}


def reason_text(feat, value):
    """把 SHAP 貢獻最大的特徵轉成一句白話，例如「USB 次數 比自己過去 30 天高」"""
    if feat.startswith(('z7d_', 'z30d_')):
        win, base = feat.split('_', 1)
        days = win[1:-1]
        if base == 'first_logon_min':
            word = '晚' if value > 0 else '早'
            return f'上班時間比自己過去 {days} 天{word}（偏離 {value:+.1f}）'
        if base == 'last_logoff_min':
            word = '晚' if value > 0 else '早'
            return f'下班時間比自己過去 {days} 天{word}（偏離 {value:+.1f}）'
        word = '高' if value > 0 else '低'
        return f'{NAME[base]}比自己過去 {days} 天{word}（偏離 {value:+.1f}）'
    if feat in ('first_logon_min', 'last_logoff_min'):
        return f'{NAME[feat]} {int(value) // 60:02d}:{int(value) % 60:02d}'
    if feat == 'is_weekend':
        return '週末上班' if value else '平日上班'
    return f'{NAME[feat]}：今天 {value:g}'


if __name__ == '__main__':
    t0 = time.time()
    df, layers = s4.load()
    feats = sum((layers[k] for k in s4.GROUPS[GROUP]), [])
    rng = np.random.default_rng(s4.SEED)

    scored, top_rows, shap_rows = [], [], []
    for m in s4.TEST_MONTHS:
        # ── 訓練：與步驟 4 walk_forward 完全相同的流程 ──
        cut = m.start_time
        train = df[df['date'] < cut]
        unknown = train['first_mal'].notna() & (train['first_mal'] >= cut) & (train[LABEL] == 1)
        train = train[~unknown]
        neg = train[LABEL] == 0
        keep = ~neg | (rng.random(len(train)) < s4.NEG_KEEP)
        train = train[keep]
        y = train[LABEL].values
        w = s4.weights(y, train['user_id'].values)
        w[y == 0] /= s4.NEG_KEEP
        model = s4.make_model('RF')
        model.fit(train[feats], y, sample_weight=w)

        # ── 打分數、排名 ──
        test = df[df['month'] == m]
        test = test[~(test['first_mal'].notna() & (test['first_mal'] < cut))]
        t = test[['user_id', 'date', 'role', 'department']].copy()
        t['risk_score'] = model.predict_proba(test[feats])[:, 1]
        t['daily_rank'] = t.groupby('date')['risk_score'].rank(ascending=False, method='first').astype(int)
        t['is_top10'] = (t['daily_rank'] <= s4.TOP_K).astype(int)
        scored.append(t)

        # ── SHAP：只算前 10 名 ──
        top_idx = t.index[t['is_top10'] == 1]
        X = test.loc[top_idx, feats]
        sv = shap.TreeExplainer(model).shap_values(X)
        sv = sv[1] if isinstance(sv, list) else sv[..., 1]     # 取「是內鬼」那一類的貢獻
        sh = pd.DataFrame(sv, columns=[f'shap_{f}' for f in feats], index=top_idx)
        val = X.add_prefix('val_')
        shap_rows.append(pd.concat([t.loc[top_idx, ['user_id', 'date']], sh, val], axis=1))
        for row_i, idx in enumerate(top_idx):
            order = np.argsort(-sv[row_i])[:3]                  # 往「更可疑」推最多的 3 個特徵
            r = t.loc[idx, ['date', 'daily_rank', 'user_id', 'role', 'department', 'risk_score']].to_dict()
            for k, j in enumerate(order, 1):
                r[f'reason{k}'] = reason_text(feats[j], X.iloc[row_i, j])
                r[f'reason{k}_feature'] = feats[j]
                base = feats[j].split('_', 1)[1] if feats[j].startswith('z') else feats[j]
                r[f'reason{k}_category'] = NAME[base]          # 原因類別（不含數值），Power BI 分組用
            top_rows.append(r)
        print(f'[{time.time() - t0:5.0f}s] {m} 完成（前 10 名 {len(top_idx)} 筆）', flush=True)

    risk = pd.concat(scored, ignore_index=True)
    pd.concat(shap_rows, ignore_index=True).to_parquet(OUT / 'shap_top10.parquet', index=False)
    top = pd.DataFrame(top_rows).sort_values(['date', 'daily_rank'])
    # 欄位順序固定：原本 12 欄在前，原因類別放最後（避免 Power BI 既有查詢讀錯欄）
    cat_cols = [f'reason{k}_category' for k in (1, 2, 3)]
    top = top[[c for c in top.columns if c not in cat_cols] + cat_cols]

    # ── 驗證：分數必須和步驟 4 的主模型一致 ──
    ref_path = OUT / 'test_scores.parquet'
    if ref_path.exists():
        ref = pd.read_parquet(ref_path, columns=['user_id', 'date', f'{GROUP}|RF|{LABEL}'])
        chk = risk.merge(ref, on=['user_id', 'date'])
        diff = (chk['risk_score'] - chk[f'{GROUP}|RF|{LABEL}']).abs().max()
        print(f'與步驟 4 分數最大差異：{diff:.2e}（應為 0）')

    # ── 答案與驗證表（只給「模型驗證」頁） ──
    lab = pd.read_parquet(OUT / 'labels.parquet')
    ans = (lab[lab['is_insider'] == 1].drop_duplicates('user_id')
           [['user_id', 'scenario', 'first_mal', 'last_mal']].copy())
    ans['scenario'] = ans['scenario'].astype(int)
    ans['scenario_name'] = ans['scenario'].map(SCENARIO_NAME)

    ev = pd.read_csv(OUT / 'results_insiders.csv')
    ev = ev[ev['實驗'] == f'{GROUP}|RF|{LABEL}'][['user_id', 'scenario', 'first_mal', 'first_alert', 'lead_days']]
    ev['scenario_name'] = ev['scenario'].astype(int).map(SCENARIO_NAME)

    # ── 匯出（utf-8-sig：Excel／Power BI 開中文不亂碼） ──
    for d in (risk, top):
        d['date'] = pd.to_datetime(d['date']).dt.date
    risk['risk_score'] = risk['risk_score'].round(4)
    top['risk_score'] = top['risk_score'].round(4)
    top.to_csv(PBI / 'top10_daily.csv', index=False, encoding='utf-8-sig')
    risk.to_csv(PBI / 'risk_daily.csv', index=False, encoding='utf-8-sig')
    ans.to_csv(PBI / 'answer_key.csv', index=False, encoding='utf-8-sig')
    ev.to_csv(PBI / 'model_validation.csv', index=False, encoding='utf-8-sig')

    print(f'\n完成（{time.time() - t0:.0f} 秒），輸出在 output/powerbi/')
    print(f'  top10_daily.csv       {len(top):,} 列')
    print(f'  risk_daily.csv        {len(risk):,} 列（{risk.date.min()} ~ {risk.date.max()}）')
    print(f'  answer_key.csv        {len(ans)} 列')
    print(f'  model_validation.csv  {len(ev)} 列')
    print('\n最常出現的風險原因（前 10 名名單中）：')
    print(top['reason1_feature'].map(lambda f: f.split('_', 1)[1] if f.startswith('z') else f)
          .map(NAME).value_counts().head(8).to_string())
