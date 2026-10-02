# 第二部分：內部威脅事前預防機制（Machine Learning）

在第一部分「日常行為偵測儀表板」之外，加入 **OCEAN 五大人格**與組織資訊，訓練機器學習模型，評估「哪些人在行為尚未異常前，就屬於較高風險」。

> 本文件為第二部分的規劃與進度紀錄，完成後再將簡述版併回總 README。

---

## 一、此專案貢獻

本專題的貢獻不在模型的預測數值，而在建立一套**可移植的內部威脅分析框架**，包含：

1. **資料整合流程**：將多來源日誌整理成「每人每日」行為特徵表，再彙整為「每人一筆」的風險輪廓
2. **以人為單位的評估方法**：依時間切分訓練與測試資料，並以「風險前 N 名中命中幾人」衡量成效，貼近資安人員的實際調查量能

企業可將自身日誌套入同一框架重新訓練，並以相同標準檢驗成效。

此框架的邏輯——**建立個人基準線、偵測偏離、以人為單位評估成效**——也可延伸至其他異常分析領域，例如金融交易盜刷偵測、醫療保險詐領、電商帳號盜用等。

### 對企業的實際價值

- **可套用的流程模板**：企業換上自己的 AD 登入、DLP、Proxy、郵件閘道日誌即可重新訓練
- **冷啟動**：多數企業沒有已確認的內鬼名單，可先用合成資料把流程與儀表板建好，累積真實標籤後再替換
- **檢驗廠商說法的評估標準**：準確率會騙人（全猜正常也有 99.6%），應問「每天只能查 10 人時，前 10 名命中幾個」
- **人員資料的實務替代**：企業實際上不太可能讓員工做人格測驗，較可行的是 HR 既有資訊（提出離職、考績下滑、調職降職）

---

## 二、文獻研討

### 主要參考文獻

| 代號 | 文獻 | 與本專題的關係 |
|---|---|---|
| [GL13] | Glasser, J. & Lindauer, B. (2013). *Bridging the Gap: A Pragmatic Approach to Generating Insider Threat Data.* IEEE Security and Privacy Workshops. DOI: 10.1109/SPW.2013.37 [PDF](https://www.ieee-security.org/TC/SPW2013/papers/data/5017a098.pdf) | **CERT 資料集原始論文**，說明資料如何生成與使用限制 |
| [Le19] | Le, D. C. & Zincir-Heywood, A. N. (2019). *Machine Learning based Insider Threat Modelling and Detection.* IEEE/IFIP DISSECT Workshop. [PDF](https://web.cs.dal.ca/~lcd/pubs/lcd_dissect19.pdf)（期刊版：Le 等 (2020), *Analyzing Data Granularity Levels for Insider Threat Detection Using Machine Learning*, IEEE TNSM） | 比較資料粒度、時間切分、以人為單位評估 |
| [Ye25] | Ye 等 (2025). *Research on insider threat detection based on personalized federated learning and behavior log analysis.* Scientific Reports. [連結](https://pmc.ncbi.nlm.nih.gov/articles/PMC12127438/) | 同樣使用 r4.2，並納入 psychometric 與 LDAP |
| [Bowie26] | Bowie, C., Larijani, H. & Qureshi, A. (2026). *Human Behaviour as a Predictor of Insider Threat: A PRISMA Systematic Literature Review and a Novel Ensemble-Based Detection Model.* Information, 17(7), 627. DOI: 10.3390/info17070627 | 以人為單位評估；揭示極度不平衡下 precision 偏低的問題 |
| [KU25] | Kamatchi, K. & Uma, E. (2025). *Insights into user behavioral-based insider threat detection: systematic review.* International Journal of Information Security, 24:88. [DOI](https://doi.org/10.1007/s10207-025-01002-6) | 總 README 文獻 1，行為偵測（UBITD）綜述 |
| [HVA26] | Papatsaroucha, D. 等 (2026). *Human Vulnerability Assessment in Cybersecurity.* arXiv:2605.22119. [PDF](https://arxiv.org/pdf/2605.22119) | 總 README 文獻 2，主張納入「人」的因素 |
| [RS25] | Ruohonen, J. & Saddiqa, M. (2025). *What Do We Know About the Psychology of Insider Threats?* EAI ICDF2C. [arXiv:2407.05943](https://arxiv.org/abs/2407.05943) | 指出內部威脅心理學缺乏穩固理論 |

### 資料集原始論文 [GL13] 重點

CERT 資料集由 CMU SEI 與 ExactData 在美國 DARPA ADAMS 計畫下產出。因真實企業日誌牽涉法律、隱私與商業機密，改以模擬器生成 500 天、整間公司的電腦紀錄。

**模擬器的心理測驗模型**：每位員工一開始就被指定固定的人格特質，外加一個會隨事件變動的「工作滿意度」。人格與滿意度如何影響行為，參考兩篇組織心理學研究：

- Mount, Ilies & Johnson (2006)：人格特質透過「工作滿意度」影響反生產工作行為（Personnel Psychology, 59, 591–622）
- Cullen 等 (2011)：五大人格與網路上的反生產行為（SIOP 研討會海報）

**作者舉的劇本範例**：

```
部門裁員 → 同事從 LDAP 消失 → 當事人工作滿意度下降
        → 上下班變得不準時（logon/logoff 時間）→ 把文件上傳到 Dropbox（HTTP 紀錄）
```

**作者自己點出的限制**：

1. **適合「驗證」，不適合「發現」**：可驗證「系統能抓到 USB 用量前 0.1% 的人」；不能證明「USB 用量大的人比較可能是內鬼」，因為那是設計者的假設
2. **參數多半是設計者自訂的**：無法用來證實「正常人與惡意人員的行為差異」理論
3. **資料比真實世界乾淨**：真實日誌的雜訊與缺漏遠比模擬資料多

### 前人研究給本專題的 6 個建議

| # | 建議 | 出處 | 本專題的做法 |
|---|---|---|---|
| 1 | 用天或週去平均，可能把惡意行為「平均掉」；粒度應依目的選擇 | [Le19] | 第一部分用「每人每日」偵測事件；第二部分用「每人一筆」看犯案前整體輪廓 |
| 2 | 依時間切分訓練與測試；訓練資料中的「正常人」只在觀察期內保證正常 | [Le19] | 固定長度觀察窗＋犯案前切點 |
| 3 | 成效要以「抓到幾個人」計算，而非「抓到幾筆資料」；Bowie26 recall 100% 但 precision 僅 0.004 | [Le19]、[Bowie26] | 以「風險前 N 名命中幾人」與 PR-AUC 評估，不看準確率 |
| 4 | Logistic Regression 作基準（好解釋、輸出機率）；Random Forest precision 高，適合人力有限的情境 | [Le19] | LR＋Random Forest＋XGBoost 三者比較 |
| 5 | 特徵＝次數＋統計量（平均、標準差）＋使用者資訊（LDAP） | [Le19]、[Ye25] | 每人輪廓沿用此設計；Le 團隊開源工具 [lcd-dal/feature-extraction-for-CERT-insider-threat-test-datasets](https://github.com/lcd-dal/feature-extraction-for-CERT-insider-threat-test-datasets)（MIT）可用於交叉驗證 |
| 6 | OCEAN 與惡意行為的關聯是資料生成器依心理學研究設定的 | [GL13]、[RS25] | 結論定位為「驗證做法可行」，不宣稱「人格能預測犯罪」 |

### 站在巨人肩膀上：前人做到哪、本專題接著做什麼

| 前人已做 | 本專題沿用 | 本專題延伸 |
|---|---|---|
| 不同資料粒度比較 [Le19] | 依目的選擇每日／每人粒度 | — |
| 時間切分、以人為單位評估 [Le19] | 犯案前觀察窗、風險前 N 名 | — |
| OCEAN 與其他特徵一併放入模型 [Ye25] | 使用 OCEAN＋LDAP | 以 SHAP 解釋每位員工的風險原因 |
| 工作滿意度影響上下班準時度 [GL13] | — | **新增「上下班時間波動」特徵，作為滿意度的間接指標** |

> 不做「有／無人員資料」對照實驗的原因：依 [GL13]，本資料集中人格對行為的影響是生成器設定進去的，對照結果只會重新驗證資料作者的設定；而真實世界中人格能否預測內部威脅，文獻尚無定論 [RS25]。因此本專案直接採用行為＋人員資料建模。
>
> 另外 [Ye25] 指標接近 0.997，但採 80/20 切分，未確認是否依時間或依人切分，不宜與本專題分數直接比較。

---

## 三、接下來要做的事情

### 已知資料現況

- 每人每日特徵表：33 萬筆、1,000 人，其中 **70 人**為惡意人員（含 OCEAN、部門、職稱、主管欄位）
- 資料期間：2010/01/02～2011/05/17
- 惡意人員第一次犯案前，最少有 111 天、中位數 192 天的正常紀錄
- 第一次犯案時間分散於 2010/06～2011/04

### 執行步驟

```
① 每天一筆 → 每人一筆  →  ② 模型訓練與比較  →  ③ 評估  →  ④ 解釋＋匯出給 Power BI
```

| 步驟 | 內容 | 預計程式 |
|---|---|---|
| ① 建立每人輪廓 | 每人取固定長度觀察窗；惡意人員取犯案前、一般員工配對隨機假切點；彙整次數、平均、標準差、OCEAN、LDAP | `01_build_user_profile.py` |
| ② 模型訓練與比較 | 行為＋人員資料，比較 LR／Random Forest／XGBoost | `02_train_compare.py` |
| ③ 評估 | 5 折交叉驗證；風險前 N 名命中數、PR-AUC | 同上 |
| ④ 解釋與匯出 | SHAP 列出每人前三大風險原因；匯出 `user_risk_profile.csv` 接 Power BI | `03_explain_export.py` |

### 待決定事項

- [ ] **觀察窗長度**：30 天／**90 天（建議）**／全部犯案前天數
- [ ] **是否留空檔**：觀察窗結束於犯案前 14 天（建議），讓模型「提早兩週」預警
- [ ] **天數不足的員工**（早期離職者）：排除，或保留並加一欄「實際觀察天數」
- [ ] **是否加入「上下班時間波動」特徵**（依 [GL13] 劇本，建議加入）
- [ ] **執行順序**：先做第二部分 ML（建議）／先補 Isolation Forest 每日異常分數／兩者並行

### 後續延伸（第二部分完成後）

- Isolation Forest 每日異常分數（非監督式，每人跟自己平常比），與第二部分的長期風險名單並列呈現：
  - **長期風險名單**（第二部分，看「人」）
  - **今日異常事件**（第一部分強化，看「事件」）
- Power BI：首頁加「AI 高風險人數」與 Top 10；單一員工頁加風險走勢；整體頁加部門 × 日期熱力圖；選配「模型驗證」頁
- 更新 Streamlit UI
- 完成後將簡述版併回總 README
