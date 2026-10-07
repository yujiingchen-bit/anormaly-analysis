# Power BI 匯入與製作說明（第二部分：AI 風險預警）

> 資料來源：`output/powerbi/`（由 `run_05.bat` 產生）
> 主模型：G1（只用行為）× Random Forest × 30 天標籤；期間 2010/8/1～2011/5/17

---

## 一、四個檔案

| 檔案 | 一列是什麼 | 主要欄位 | 用在哪一頁 |
|---|---|---|---|
| `top10_daily.csv` | 某天的前 10 名之一 | date、daily_rank、user_id、role、department、risk_score、reason1～3、reason1～3_category | 首頁 |
| `risk_daily.csv` | 某人某天 | user_id、date、role、department、risk_score、daily_rank、is_top10 | 單一員工頁、部門熱力圖 |
| `answer_key.csv` | 一個內鬼 | user_id、scenario_name、first_mal、last_mal | **只給**模型驗證頁 |
| `model_validation.csv` | 一個評估內鬼 | user_id、scenario_name、first_mal、first_alert、lead_days | **只給**模型驗證頁 |

> `reason1`～`reason3`：完整中文原因（含數值），放在名單上；`reason1_category`～`reason3_category`：原因類別（不含數值），拿來分組計數；`reason*_feature` 是程式用的英文名稱，報表不需要。

---

## 二、匯入（約 5 分鐘）

1. **常用 → 取得資料 → 文字/CSV**，依序選四個檔案 → 每個都按 **載入**
2. **檢查型別**（Power Query 或資料檢視）：
   - `date`、`first_mal`、`last_mal`、`first_alert` → **日期**
   - `risk_score` → **十進位數字**；`daily_rank`、`lead_days`、`is_top10` → **整數**
3. 若中文變亂碼：Power Query 中把「檔案原點」改為 **65001: Unicode (UTF-8)**

---

## 三、建立關聯（模型檢視）

| 從 | 到 | 關聯 |
|---|---|---|
| `risk_daily[user_id]` | `answer_key[user_id]` | 多對一 |
| `model_validation[user_id]` | `answer_key[user_id]` | 一對一 |
| （選配）`risk_daily[user_id]` | 第一部分的員工表 `[user_id]` | 多對一 |
| （選配）`risk_daily[date]` | 第一部分的日期表 `[Date]` | 多對一 |

> `top10_daily` 與 `risk_daily` 不必建關聯，各自用自己的日期篩選器即可；若想共用同一個日期篩選器，兩者都連到第一部分的日期表。

---

## 四、建立量值（DAX）

在 `risk_daily` 上按右鍵 → 新增量值，逐一貼上：

```DAX
高風險人數 = CALCULATE(DISTINCTCOUNT(risk_daily[user_id]), risk_daily[risk_score] >= 0.5)

平均風險分數 = AVERAGE(risk_daily[risk_score])

進入Top10次數 = SUM(risk_daily[is_top10])
```

在 `model_validation` 上：

```DAX
評估內鬼數 = COUNTROWS(model_validation)

犯案前預警人數 = CALCULATE(COUNTROWS(model_validation), model_validation[lead_days] > 0)

提早天數中位數 = MEDIAN(model_validation[lead_days])
```

---

## 五、四個頁面

### 頁 1　首頁：今日 AI 高風險名單（全體員工）

**版面**：左＝今日指標卡片｜右上＝Top 10 名單（誰）｜右下左＝部門分布（哪裡）｜右下右＝**今日高風險原因（為什麼）**

| 視覺效果 | 設定 |
|---|---|
| 交叉分析篩選器 | `top10_daily[date]`（或第一部分日期表，需與 `top10_daily[date]` 建關聯） |
| 資料表：Top 10 名單 | `daily_rank`、`user_id`、`employee_name`、`risk_score`、**`reason1`**，依 `daily_rank` 遞增 |
| 環圈圖：高風險員工分布部門 | 圖例 `department`、值 `user_id`（計數） |
| **群組橫條圖：今日高風險原因** | Y 軸 `reason1_category`、X 軸 `user_id`（計數），依計數遞減排序 |

**Top 10 名單的兩個修正**
- `risk_score` 的總和 → 值欄位右鍵改為 **「不要摘要」** 或 **「最大值」**，標題改為「風險分數」
- 加入 **`reason1`** 欄（第一大風險原因），名單才回答得了「為什麼是他」；欄寬拉寬或開啟自動換行
- `risk_score` 欄加 **設定格式化 → 資料橫條**，一眼看出風險高低

**今日高風險原因（紅框位置）**
- 標題：「今日高風險原因」；副標：「Top 10 員工的第一大原因」
- 例：2010/8/20 → 瀏覽網頁數 6 人、下班後登入次數 2 人、使用電腦台數 1 人、USB 次數 1 人
- 想看更完整可改用三欄合計：把 `reason1_category`～`reason3_category` 在 Power Query **取消樞紐** 成一欄再計數

> 首頁三塊剛好回答調查人員的三個問題：**誰**（Top 10）、**在哪個部門**（環圈圖）、**為什麼**（原因橫條圖）。

- 建議預設日期選 **2010/12/30**：可看到內鬼 FMG0527 在第一次犯案（2011/1/5）前 6 天就排第 3 名，原因是下班後 USB 次數

### 頁 2　單一員工：風險走勢

| 視覺效果 | 設定 |
|---|---|
| 交叉分析篩選器 | `risk_daily[user_id]`（可搜尋） |
| 折線圖 | X 軸 `risk_daily[date]`、Y 軸 `平均風險分數` |
| 卡片 | `進入Top10次數` |
| 資料表 | 該員工在 `top10_daily` 的日期與 reason1～3 |

- 折線圖可加 **常數線 Y = 0.5** 當警戒線
- 示範人選：FMG0527（情境 1）、CCL0068（情境 2）

### 頁 3　部門 × 日期熱力圖

| 視覺效果 | 設定 |
|---|---|
| 矩陣 | 列 `risk_daily[department]`、欄 `risk_daily[date]`（階層選「月」或「週」）、值 `進入Top10次數` |

- 值欄 **設定格式化 → 背景色彩**，低＝白、高＝紅，就成為熱力圖

### 頁 4　模型驗證（選配，含答案）

| 視覺效果 | 設定 |
|---|---|
| 卡片 × 3 | `評估內鬼數`（45）、`犯案前預警人數`（38）、`提早天數中位數` |
| 群組橫條圖 | Y 軸 `model_validation[user_id]`、X 軸 `lead_days`、圖例 `scenario_name` |
| 資料表 | `answer_key` 全部欄位 |

- 橫條圖依 `lead_days` 遞減排序；正數＝犯案前就預警
- 頁面標題註明「含答案，僅供驗證模型」，與前三頁區隔

---

## 六、完成後檢查

- [ ] 頁 1 選 2010/12/30，Top 10 第 3 名是 FMG0527
- [ ] 頁 4 卡片顯示 45 人、犯案前預警 38 人
- [ ] 中文欄位與原因沒有亂碼
