"""
06_figures.py
第 6 步：把第 5 節的統計結果與第 7 節的 SHAP 畫成圖，給 method.md／簡報使用

輸入：output/results_insiders.csv、results_summary.csv、shap_top10.parquet、powerbi/answer_key.csv
輸出：figures/*.png

執行方式（在 MachineLearning 資料夾裡）：
  python scripts/06_figures.py
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from matplotlib import font_manager
from matplotlib.patches import Patch
from scipy.stats import wilcoxon

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'output'
FIG = BASE / 'figures'
FIG.mkdir(exist_ok=True)

# ── 樣式 ──────────────────────────────────────────────────
for f in ['Microsoft JhengHei', 'Noto Sans CJK TC', 'PingFang TC', 'Heiti TC']:
    if any(f in x.name for x in font_manager.fontManager.ttflist):
        plt.rcParams['font.family'] = f
        break
plt.rcParams.update({
    'axes.unicode_minus': False, 'figure.dpi': 150, 'savefig.dpi': 150,
    'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb',
    'axes.edgecolor': '#c9c8c3', 'axes.labelcolor': '#52514e',
    'xtick.color': '#52514e', 'ytick.color': '#52514e', 'text.color': '#0b0b0b',
    'axes.spines.top': False, 'axes.spines.right': False,
    'axes.grid': True, 'grid.color': '#ebeae6', 'grid.linewidth': 0.8, 'axes.axisbelow': True,
    'font.size': 10, 'axes.titlesize': 12, 'axes.titleweight': 'bold',
})
BLUE, ORANGE, AQUA, GRAY, INK2 = '#2a78d6', '#eb6834', '#1baf7a', '#a3a29c', '#52514e'
SC_COLOR = {1: BLUE, 2: ORANGE, 3: AQUA}
SC_NAME = {1: '情境1 洩密', 2: '情境2 跳槽', 3: '情境3 報復'}

NAME = {
    'logon_cnt': '登入次數', 'ah_logon_cnt': '下班後登入', 'first_logon_min': '上班時間',
    'last_logoff_min': '下班時間', 'n_pc': '使用電腦台數', 'other_pc_logon_cnt': '登入他人電腦',
    'usb_cnt': 'USB 次數', 'ah_usb_cnt': '下班後 USB', 'file_cnt': '複製到 USB 檔案數',
    'ah_file_cnt': '下班後複製檔案', 'exe_file_cnt': '複製執行檔', 'email_cnt': '寄信數',
    'ah_email_cnt': '下班後寄信', 'ext_rcpt_cnt': '外部收件人數', 'max_rcpt_cnt': '單封最多收件人',
    'attach_cnt': '附件數', 'http_cnt': '瀏覽網頁數', 'ah_http_cnt': '下班後瀏覽',
    'n_domain': '瀏覽網站數', 'leak_cnt': 'wikileaks 瀏覽', 'job_cnt': '求職網站瀏覽',
    'cloud_cnt': '雲端分享瀏覽', 'keylog_cnt': 'keylog 瀏覽', 'is_weekend': '週末上班',
}


def zh(feat):
    """特徵英文名 → 中文；偏離量加註視窗，例：USB 次數（30 天偏離）"""
    if feat.startswith(('z7d_', 'z30d_')):
        win, base = feat.split('_', 1)
        return f'{NAME[base]}（{win[1:-1]} 天偏離）'
    return NAME[feat]


def save(fig, name):
    fig.savefig(FIG / name, bbox_inches='tight')
    plt.close(fig)
    print('  ✓', name)


def strip(ax, groups, labels, colors, title, xlabel='提早天數（正數＝犯案前就預警）'):
    """每個內鬼一個點（上下抖動避免重疊），粗線＝中位數"""
    rng = np.random.default_rng(0)
    for i, (vals, c) in enumerate(zip(groups, colors)):
        y = i + rng.uniform(-0.18, 0.18, len(vals))
        ax.scatter(vals, y, s=22, color=c, alpha=0.75, edgecolor='#fcfcfb', linewidth=0.6, zorder=3)
        med = np.median(vals)
        ax.plot([med, med], [i - 0.32, i + 0.32], color='#0b0b0b', linewidth=2.2, zorder=4)
        ax.text(31.5, i, f'中位數 {med:g} 天', va='center', fontsize=9, color=INK2)
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.axvline(0, color=INK2, linewidth=1, linestyle='--', zorder=2)
    ax.set_xlim(-1, 31)
    ax.set_xlabel(xlabel)
    ax.set_title(title, loc='left')
    ax.grid(axis='y', visible=False)


if __name__ == '__main__':
    r = pd.read_csv(OUT / 'results_insiders.csv')
    R = pd.read_csv(OUT / 'results_summary.csv').set_index('實驗')
    lead = r.pivot_table(index='user_id', columns='實驗', values='lead_days')
    sc = r.drop_duplicates('user_id').set_index('user_id')['scenario'].astype(int)
    p = lambda a, b: wilcoxon(lead[a], lead[b]).pvalue
    print('產生圖表：')

    # ── 圖 1　H1：主模型每個內鬼的提早天數 ─────────────────
    main = 'G1_A+B|RF|label_30d'
    d = pd.DataFrame({'lead': lead[main], 'sc': sc}).sort_values(['lead', 'sc'], ascending=[False, True])
    fig, ax = plt.subplots(figsize=(7, 8.5))
    ax.barh(range(len(d)), d['lead'], color=[SC_COLOR[s] for s in d['sc']], height=0.7)
    ax.set_yticks(range(len(d)), d.index, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel('提早天數（第一次犯案日 − 第一次進入每日前 10 名）')
    n_pre = (d['lead'] > 0).sum()
    zero = np.where(d['lead'].values == 0)[0]                  # 當天才預警：長條為 0，改畫一個點
    ax.scatter(np.zeros(len(zero)), zero, s=26, color=[SC_COLOR[x] for x in d['sc'].values[zero]], zorder=3)
    ax.text(0.6, zero.mean(), f'← {len(zero)} 人在第一次犯案當天預警', va='center', fontsize=9, color=INK2)
    ax.set_title(f'H1　45 名內鬼全部被預警，{n_pre} 人在犯案前（主模型 G1 × RF × 30 天，中位數 {d.lead.median():g} 天）',
                 loc='left', fontsize=11)
    ax.grid(axis='y', visible=False)
    ax.legend(handles=[Patch(color=c, label=SC_NAME[k]) for k, c in SC_COLOR.items()],
              loc='lower right', frameon=False)
    save(fig, 'fig1_h1_lead_days.png')

    # ── 圖 2　H2：特徵組比較 ─────────────────────────────
    gs = [('G1_A+B', 'G1 只用行為'), ('G2_A+B+D', 'G2 ＋人格'), ('G3_A+B+C', 'G3 ＋組織'), ('G4_A+B+C+D+E', 'G4 全部')]
    keys = [f'{g}|RF|label_14d' for g, _ in gs]
    labels = [n if i == 0 else f'{n}\n(p＝{p(keys[0], k):.3f})' for i, ((_, n), k) in enumerate(zip(gs, keys))]
    fig, ax = plt.subplots(figsize=(8, 4))
    strip(ax, [lead[k] for k in keys], labels, [BLUE, GRAY, GRAY, GRAY],
          'H2　加入人格、組織都沒有更早（RF × 14 天；p 為與 G1 比較）')
    save(fig, 'fig2_h2_feature_groups.png')

    # ── 圖 3　H2：人格洗牌 ───────────────────────────────
    a, b = 'G4_A+B+C+D+E|XGB|label_14d', 'G4_A+B+C+D+E|XGB|label_14d|人格洗牌'
    fig, ax = plt.subplots(figsize=(8, 2.6))
    strip(ax, [lead[a], lead[b]], ['真實人格', f'洗牌後\n(p＝{p(a, b):.3f})'], [BLUE, GRAY],
          '人格洗牌測試：打亂後有變差趨勢，未達顯著（G4 × XGB × 14 天）')
    save(fig, 'fig3_h2_shuffle.png')

    # ── 圖 4　H3：模型比較（四個指標各一格，避免雙軸） ───────
    ms = [('RF', 'Random Forest'), ('XGB', 'XGBoost'), ('LR', 'Logistic Regression')]
    rows = [R.loc[f'G1_A+B|{m}|label_14d'] for m, _ in ms]
    metrics = [('抓到人數', '抓到人數（共 45）', '{:.0f}'), ('提早天數_中位數', '提早天數中位數', '{:g} 天'),
               ('Precision@10', 'Precision@10', '{:.3f}'), ('PR_AUC', 'PR-AUC（亂猜＝0.007）', '{:.3f}')]
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.2), sharey=True)
    for ax, (col, title, fmt) in zip(axes, metrics):
        vals = [x[col] for x in rows]
        ax.barh(range(3), vals, color=[BLUE, GRAY, GRAY], height=0.6)
        for i, v in enumerate(vals):
            ax.text(v, i, ' ' + fmt.format(v), va='center', fontsize=9, color=INK2)
        ax.set_title(title, fontsize=10, loc='left')
        ax.set_xlim(0, max(vals) * 1.35)
        ax.grid(axis='y', visible=False)
    axes[0].set_yticks(range(3), [n for _, n in ms])
    axes[0].invert_yaxis()
    fig.suptitle('H3　Random Forest 各項指標最佳（G1 × 14 天）', x=0.01, ha='left', fontweight='bold')
    fig.tight_layout()
    save(fig, 'fig4_h3_models.png')

    # ── 圖 5　H3：標籤窗比較 ─────────────────────────────
    ks = [f'G1_A+B|RF|label_{n}d' for n in (7, 14, 30)]
    labels = ['7 天', f'14 天\n(vs 7：p＝{p(ks[0], ks[1]):.3f})', f'30 天\n(vs 7：p＝{p(ks[0], ks[2]):.3f})']
    fig, ax = plt.subplots(figsize=(8, 3.4))
    strip(ax, [lead[k] for k in ks], labels, [GRAY, GRAY, BLUE],
          'H3　三種標籤窗無顯著差異；30 天數值最高（G1 × RF）')
    save(fig, 'fig5_h3_label_window.png')

    # ── SHAP 圖（需先跑步驟 5 產生 shap_top10.parquet） ─────
    sp = OUT / 'shap_top10.parquet'
    if not sp.exists():
        print('  （找不到 shap_top10.parquet，略過 SHAP 圖；請先執行 run_05.bat）')
        raise SystemExit
    s = pd.read_parquet(sp)
    feats = [c[5:] for c in s.columns if c.startswith('shap_')]
    S = s[[f'shap_{f}' for f in feats]].values
    V = s[[f'val_{f}' for f in feats]]
    V.columns = [zh(f) for f in feats]

    # 圖 6　SHAP 特徵重要度
    imp = pd.Series(np.abs(S).mean(0), index=[zh(f) for f in feats]).sort_values().tail(12)
    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.barh(imp.index, imp.values, color=BLUE, height=0.6)
    ax.set_xlabel('平均 |SHAP 值|（對風險分數的平均影響）')
    ax.set_title('SHAP 特徵重要度：每日 Top 10 中，影響最大的 12 個特徵', loc='left')
    ax.grid(axis='y', visible=False)
    save(fig, 'fig6_shap_importance.png')

    # 圖 7　SHAP 蜂群圖（官方圖）
    plt.figure()
    shap.summary_plot(S, V, max_display=12, show=False, plot_size=(8, 5.2))
    plt.title('SHAP 蜂群圖：紅＝特徵值高、藍＝特徵值低；往右＝提高風險', loc='left', fontsize=11, fontweight='bold')
    plt.gcf().savefig(FIG / 'fig7_shap_beeswarm.png', bbox_inches='tight', facecolor='#fcfcfb')
    plt.close('all')
    print('  ✓ fig7_shap_beeswarm.png')

    # 圖 8　各情境內鬼的 SHAP 重要度
    ans = pd.read_csv(OUT / 'powerbi' / 'answer_key.csv')
    s['sc'] = s['user_id'].map(ans.set_index('user_id')['scenario'])
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    for ax, k in zip(axes, (1, 2, 3)):
        m = s['sc'] == k
        im = pd.Series(np.abs(S[m.values]).mean(0), index=[zh(f) for f in feats]).sort_values().tail(6)
        ax.barh(im.index, im.values, color=SC_COLOR[k], height=0.6)
        ax.set_title(f'{SC_NAME[k]}（{m.sum()} 筆）', loc='left', fontsize=10)
        ax.grid(axis='y', visible=False)
        ax.tick_params(axis='y', labelsize=8.5)
    fig.suptitle('各情境內鬼進入 Top 10 時，影響最大的特徵（平均 |SHAP 值|）', x=0.01, ha='left', fontweight='bold')
    fig.tight_layout()
    save(fig, 'fig8_shap_by_scenario.png')
    print(f'\n完成，圖表在 {FIG}')
