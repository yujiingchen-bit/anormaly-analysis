from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────
# 影片設定：之後把 Power BI 操作影片放進 videos/ 資料夾，
# 或填入 YouTube 網址，把 None 換成路徑字串即可自動顯示
# 例："videos/overview.mp4" 或 "https://youtu.be/xxxx"
# ─────────────────────────────────────────────
VIDEOS = {
    "overview": None,  # 主儀表板（全體員工）
    "employee": None,  # 單一員工總覽
    "logon": None,     # 登入登出
    "http": None,      # 上網網域
    "email": None,     # Email
    "file": None,      # 檔案複製
}

st.set_page_config(page_title="內部異常行為偵測", page_icon="🛡️", layout="wide")

# ── 自訂樣式：卡片、標籤、影片預留框 ──
st.markdown(
    """
<style>
/* 縮小頁面最上方的空白（Streamlit 預設約 6rem） */
.block-container {padding-top: 1.5rem;}
.hero {padding: 20px 28px; border-radius: 16px;
       background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%); color: #fff; margin-bottom: 8px;}
.hero h1 {color:#fff; margin:0 0 6px 0; font-size: 2.1rem;}
.hero p {color:#dbe8f5; margin:0; font-size:1.05rem;}
.card {border:1px solid rgba(128,128,128,.25); border-radius:14px; padding:18px 20px; height:100%;
       background: rgba(128,128,128,.05);}
.card h4 {margin-top:0;}
.badge {display:inline-block; padding:2px 10px; border-radius:999px; font-size:.8rem; font-weight:600; margin-right:6px;}
.done {background:#d1fae5; color:#065f46;}
.wip {background:#fef3c7; color:#92400e;}
.chip {display:inline-block; padding:6px 12px; margin:4px; border-radius:10px; font-size:.9rem;}
.chip-on {background:#2d6a9f; color:#fff;}
.chip-off {background:rgba(128,128,128,.15); color:gray;}
.video-slot {border:2px dashed #94a3b8; border-radius:14px; padding:40px 20px; text-align:center;
             color:#64748b; background:rgba(148,163,184,.08);}
.video-slot .icon {font-size:2.4rem;}
</style>
""",
    unsafe_allow_html=True,
)


def video_slot(key: str, title: str):
    """影片區：有設定就播放，沒設定就顯示預留框"""
    src = VIDEOS.get(key)
    if src and (src.startswith("http") or Path(src).exists()):
        st.video(src)
    else:
        st.markdown(
            f"""<div class="video-slot"><div class="icon">🎬</div>
            <b>{title} 操作影片</b><br>影片製作中，之後補上</div>""",
            unsafe_allow_html=True,
        )


def card(title: str, body: str):
    st.markdown(f'<div class="card"><h4>{title}</h4>{body}</div>', unsafe_allow_html=True)


# ── 頁首 ──
st.markdown(
    """<div class="hero"><h1>🛡️ 內部異常行為偵測儀表板</h1>
<p>以 CERT r4.2 內部威脅資料集，從登入登出／上網／裝置插拔／檔案複製／Email 等行為維度，
建構異常分析儀表板，並結合機器學習每日預測高風險員工。</p></div>""",
    unsafe_allow_html=True,
)

tab_frame, tab_p1, tab_p2, tab_future = st.tabs(
    ["專案框架", "第一部分：異常行為儀表板", "第二部分：機器學習", "未來應用"]
)

# ═════════════════════════════════════════════
# Tab 1：整體專案框架
# ═════════════════════════════════════════════
with tab_frame:
    st.subheader("📊 整體專案框架")
    st.caption("第一部分做「看得見異常」的儀表板，第二部分用 ML 做「預測誰有風險」，最後把預測結果接回儀表板。")

    # 流程圖（Graphviz）
    st.graphviz_chart(
        """
digraph {
  rankdir=LR; bgcolor="transparent";
  node [shape=box, style="rounded,filled", fontname="Microsoft JhengHei", fontsize=12, color="#94a3b8"];
  edge [color="#64748b"];
  raw [label="CERT r4.2\\n原始 CSV", fillcolor="#e2e8f0"];
  subgraph cluster1 { label="第一部分（已完成）"; style="rounded"; color="#10b981"; fontname="Microsoft JhengHei";
    sql [label="SQL Server ETL\\n7 大事實/維度表", fillcolor="#d1fae5"];
    pbi [label="Power BI\\n星狀模型與量值", fillcolor="#d1fae5"];
    dash [label="異常分析儀表板", fillcolor="#d1fae5"];
  }
  subgraph cluster2 { label="第二部分（規劃中）"; style="rounded,dashed"; color="#f59e0b"; fontname="Microsoft JhengHei";
    wide [label="Python\\n行為寬表", fillcolor="#fef3c7"];
    ml [label="監督式 ML 模型", fillcolor="#fef3c7"];
    top [label="Top10\\n高風險員工", fillcolor="#fef3c7"];
  }
  ui [label="Streamlit UI", fillcolor="#dbeafe"];
  raw -> sql -> pbi -> dash -> ui;
  raw -> wide -> ml -> top;
  top -> dash [style=dashed, label=" 接回主儀表板", fontsize=10];
}
""",
        width="stretch",
    )

    c1, c2 = st.columns(2)
    with c1:
        card(
            '第一部分：員工異常行為儀表板 <span class="badge done">已完成</span>',
            """<ul>
<li><b>目的</b>：多行為維度建構異常分析儀表板，及早預防異常資安事件</li>
<li><b>資料清理</b>：SQL Server ETL，產出 7 大事實與維度表、員工離職狀態表</li>
<li><b>資料建模</b>：Power BI 星狀模型與量值、儀表板設計</li>
<li><b>視覺化介面</b>：Python Streamlit</li>
<li><b>版本備份</b>：GitHub 多分支</li></ul>""",
        )
    with c2:
        card(
            '第二部分：CERT 監督式機器學習 <span class="badge wip">規劃中</span>',
            """<ul>
<li><b>目的</b>：透過 ML 每日偵測高風險員工</li>
<li><b>資料清理</b>：Python 彙整 ML 行為標籤表（寬表）</li>
<li><b>資料建模</b>：主儀表板加入 Top10 高風險員工預測值</li>
<li><b>視覺化介面</b>：更新 Streamlit UI</li>
<li><b>版本備份</b>：GitHub</li></ul>""",
        )

    st.divider()

    # 背景文獻
    st.subheader("📚 背景文獻：為什麼要看「行為」？")
    st.markdown(
        "內部人員擁有**合法權限**，傳統特徵碼資安設備認不出「合法權限下的惡意操作」，"
        "因此以使用者行為為基礎的內部威脅偵測（**UBITD**）是企業的第一道防線。"
        "在 CERT 等資料集上，結合 LSTM、SVM 等模型，召回率（Recall）可達 **90%～99%**。"
    )
    st.caption(
        "Kamatchi, K. & Uma, E. (2025). Insights into user behavioral-based insider threat detection: "
        "systematic review. International Journal of Information Security, 24:88."
    )
    # 8 大類日誌：本專案涵蓋的亮色、未涵蓋的灰色
    logs = [
        ("登入登出", True), ("檔案操作", True), ("USB 裝置", True), ("網頁瀏覽", True),
        ("電子郵件", True), ("心理傾向（OCEAN）", True), ("鍵盤滑鼠動態", False), ("系統指令列", False),
    ]
    chips = "".join(f'<span class="chip {"chip-on" if on else "chip-off"}">{name}</span>' for name, on in logs)
    st.markdown(f"**UBITD 監控 8 大類日誌**（藍色為本專案涵蓋的 6 類）<br>{chips}", unsafe_allow_html=True)

    st.divider()

    # 資料集
    st.subheader("🌐 資料集：CERT Insider Threat r4.2")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("模擬員工", "1,000 人")
    m2.metric("資料期間", "17 個月", "2009/12～2011/05", delta_color="off")
    m3.metric("惡意事件", "70 件")
    m4.metric("惡意情境", "3 種")
    d1, d2 = st.columns([3, 2])
    with d1:
        st.markdown(
            "CMU CERT 製作的**合成資料**。真實企業員工 log 過於敏感無法公開，因此以模擬方式產生。"
            "內容包含登入登出、隨身碟插拔、上網、寄信、檔案複製，加上每人心理測驗分數與每月組織名冊（LDAP）。\n\n"
            "**3 種惡意情境**：離職前偷資料、販賣公司機密、蓄意破壞\n\n"
            "[👉 Kaggle 資料集連結](https://www.kaggle.com/datasets/andrihjonior/cert-insider-threat-dataset-r4-2/data)"
        )
    with d2:
        # OCEAN 五大人格：示意分數範圍（每項 10～50 分）
        ocean = pd.DataFrame({
            "特質": ["O 開放性", "C 盡責性", "E 外向性", "A 親和性", "N 神經質"],
            "最低": [10] * 5, "最高": [50] * 5,
        })
        chart = (
            alt.Chart(ocean)
            .mark_bar(size=18, cornerRadius=6, color="#2d6a9f", opacity=0.7)
            .encode(
                y=alt.Y("特質:N", sort=None, title=None),
                x=alt.X("最低:Q", scale=alt.Scale(domain=[0, 50]), title="分數範圍（10～50）"),
                x2="最高:Q",
            )
            .properties(height=200, title="OCEAN 五大人格量表")
        )
        st.altair_chart(chart, width="stretch")
        st.caption("每項 10 題 × 1～5 分；分數越高傾向越強（如 N 高代表情緒較不穩定）")

# ═════════════════════════════════════════════
# Tab 2：第一部分 — 不同維度操作方式
# ═════════════════════════════════════════════
with tab_p1:
    st.subheader("第一部分：企業內員工異常行為儀表板")

    # 資料處理流程：四步驟橫向卡片
    st.markdown("#### 🔧 資料處理流程")
    steps = [
        ("① 匯入 SQL Server", "CSV 匯入後整理事實表與維度表<br>展示區間：2010/7/20～8/20"),
        ("② 建立 View 表", "logon／email／http／file／device／psychometric／date 與彙總表"),
        ("③ 離職狀態處理", "比對每月 LDAP 名冊，推算在職／預計離職"),
        ("④ Power BI 建模", "建立星狀模型與量值，設計儀表板"),
    ]
    for col, (t, b) in zip(st.columns(4), steps):
        with col:
            card(t, f"<small>{b}</small>")

    st.markdown("#### 🔍 儀表板鑽研邏輯：由大到小")
    st.graphviz_chart(
        """
digraph {
  rankdir=LR; bgcolor="transparent";
  node [shape=box, style="rounded,filled", fontname="Microsoft JhengHei", fontsize=12, color="#94a3b8"];
  a [label="全體員工\\n主儀表板", fillcolor="#1e3a5f", fontcolor="white"];
  b [label="單一員工\\n員工總覽頁", fillcolor="#2d6a9f", fontcolor="white"];
  c1 [label="Logon/off", fillcolor="#dbeafe"]; c2 [label="HTTP Domain", fillcolor="#dbeafe"];
  c3 [label="Email", fillcolor="#dbeafe"]; c4 [label="File Copy", fillcolor="#dbeafe"];
  edge [color="#64748b"];
  a -> b [label=" 點選員工鑽研", fontsize=10]; b -> {c1 c2 c3 c4};
}
"""
    )
    st.info("核心判斷：**時間區間內的當日狀態 vs 歷史平均值**，偏離越大越可疑。")

    st.markdown("#### 🎬 各維度操作方式")
    # 每個維度：左邊說明、右邊影片
    dims = [
        ("overview", "全體員工", "主儀表板",
         ["查看當日 **Top10 高風險員工**與總異常數", "顯示今日異常員工的**分佈部門**與各行為異常數字",
          "全員登入趨勢**散佈圖**找出離群值", "異常檔案複製列表"],
         "主儀表板目前為暫定版，待第二部分完成後替換為 ML 預測結果"),
        ("employee", "單一員工", "員工總覽頁",
         ["由主儀表板**點選員工鑽研**進入", "查看該員工在時間區間內**各行為異常數量**", "顯示**在職／預計離職**狀態"],
         None),
        ("logon", "登入登出", "Logon/off",
         ["時間區間內登入登出**明細**", "登入**時間分布**", "與過去平均值比較，確認是否有異常跡象"],
         None),
        ("http", "上網網域", "HTTP Domain",
         ["時間區間內上網**網域明細**", "上網時間與次數分布", "**不重複網域數** vs 平均值"],
         None),
        ("email", "Email", "Email",
         ["時間區間內寄信明細", "一日內寄信**時間趨勢**", "**外部收件人佔比**、**單信平均附件大小** vs 過去平均"],
         None),
        ("file", "檔案複製", "File Copy",
         ["時間區間內**異常複製**明細", "比對 **file_header 與實際檔名**，不符者視為疑似竄改", "異常複製數 vs 過去平均"],
         None),
    ]
    sub_tabs = st.tabs([d[1] for d in dims])
    for sub, (key, label, page, points, note) in zip(sub_tabs, dims):
        with sub:
            left, right = st.columns([2, 3])
            with left:
                st.markdown(f"##### {label}｜{page}")
                st.markdown("\n".join(f"- {p}" for p in points))
                if note:
                     st.caption(f"⚠️ {note}")
            with right:
                video_slot(key, page)

# ═════════════════════════════════════════════
# Tab 3：第二部分 — 內容產出中
# ═════════════════════════════════════════════
with tab_p2:
    st.subheader("第二部分：CERT 資料集監督式機器學習（ML）")
    st.warning("🚧 內容產出中，完成後會陸續更新")
    st.markdown("每日偵測員工行為維度，預測高風險員工。")

    todo = [
        ("🧹 資料清理", "Python 彙整 ML 行為標籤表（寬表）"),
        ("🧠 模型訓練", "模型選擇與訓練"),
        ("📏 模型評估", "評估指標（Recall 等）"),
        ("🔗 接回儀表板", "預測結果接回 Power BI 主儀表板（Top10 高風險員工）"),
        ("🖥️ 更新 UI", "更新 Streamlit 展示頁"),
    ]
    for col, (t, b) in zip(st.columns(5), todo):
        with col:
            card(t, f'<small>{b}</small><br><br><span class="badge wip">待補</span>')
    st.progress(0, text="進度 0 / 5")

# ═════════════════════════════════════════════
# Tab 4：未來應用
# ═════════════════════════════════════════════
with tab_future:
    st.subheader("未來應用")
    f1, f2, f3 = st.columns(3)
    with f1:
        card("🏭 跨產業複用", "「從大維度到小維度」的儀表板邏輯，可套用到製造業異常檢測、流程異常分析，加速每日排查。")
    with f2:
        card("⏰ 提早預警", "以歷史資料建模，讓系統與工程師提早鎖定高風險族群，提早排除。")
    with f3:
        card("🤖 AI 時代的新資料源",
             "企業導入內部 AI 後，AI 查詢 log 也能套用同一套系統——「誰在異常時段對 AI 工具大量查詢／貼上」，"
             "與 CERT 裡「誰在異常時段大量存取檔案」是同一類問題。")
