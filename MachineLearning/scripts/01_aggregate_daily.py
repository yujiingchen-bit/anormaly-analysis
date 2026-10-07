"""
01_aggregate_daily.py
第 1 步：把原始紀錄（一筆一筆的事件）整理成「每人每天一列」

做法：用 DuckDB 直接對 CSV 下 SQL，一邊讀一邊算，不用把整個檔案載入記憶體
     （http.csv 有 14.5 GB，用 pandas 直接讀會當機）

輸出：output/daily_logon.parquet、daily_device.parquet、daily_file.parquet、
      daily_email.parquet、daily_http.parquet

執行方式（在 MachineLearning 資料夾裡）：
  python scripts/01_aggregate_daily.py              → 五個來源全部跑（http 最慢）
  python scripts/01_aggregate_daily.py logon        → 只跑 logon（建議先用這個測試）
  python scripts/01_aggregate_daily.py logon device → 只跑這兩個
"""
import sys
import time
from pathlib import Path

import duckdb

# ── 設定 ──────────────────────────────────────────────────
# 路徑以「這支程式所在的位置」為準：scripts → MachineLearning → 專案根目錄
BASE = Path(__file__).resolve().parents[1]     # MachineLearning
RAW = BASE.parent / 'archive' / 'r4.2'         # 原始 CSV 的位置
OUT = BASE / 'output'                          # 輸出位置
OUT.mkdir(exist_ok=True)

# 「下班後」的定義，沿用第一部分：6～20 點以外
AFTER_HOURS = "hour(ts) NOT BETWEEN 6 AND 20"

# 原始日期長這樣：01/02/2010 06:49:00
TS = "strptime(date, '%m/%d/%Y %H:%M:%S')"

con = duckdb.connect()
con.execute(f"SET temp_directory = '{(OUT / 'duckdb_tmp').as_posix()}'")  # 記憶體不夠時，暫存到硬碟


def read_csv(name):
    """讀原始 CSV：所有欄位先當文字讀，避免自動判斷型態出錯"""
    return f"read_csv('{(RAW / name).as_posix()}', header=true, all_varchar=true)"


def save(sql, name):
    """執行 SQL，把結果存成 parquet"""
    path = (OUT / f'daily_{name}.parquet').as_posix()
    con.execute(f"COPY ({sql}) TO '{path}' (FORMAT parquet)")
    return path


# ── 1. logon：登入登出 ────────────────────────────────────
# 看什麼：登入次數、下班後登入、幾點來幾點走、有沒有登入別人的電腦
def logon():
    # 每個人「自己的電腦」＝ 2010 年 1 月最常登入的那台
    # 只用第一個月，不用整段期間：避免用到未來的資訊
    main_pc = f"""
        SELECT user, arg_max(pc, n) AS main_pc
        FROM (
            SELECT user, pc, count(*) AS n
            FROM {read_csv('logon.csv')}
            WHERE activity = 'Logon' AND {TS} < DATE '2010-02-01'
            GROUP BY user, pc
        )
        GROUP BY user
    """
    sql = f"""
        WITH t AS (
            SELECT l.user, l.pc, l.activity, {TS} AS ts, m.main_pc
            FROM {read_csv('logon.csv')} l
            LEFT JOIN ({main_pc}) m USING (user)
        )
        SELECT
            user AS user_id,
            CAST(ts AS DATE)                                              AS date,
            count(*) FILTER (activity = 'Logon')                          AS logon_cnt,
            count(*) FILTER (activity = 'Logon' AND {AFTER_HOURS})        AS ah_logon_cnt,
            -- 幾點來、幾點走：換成「當天第幾分鐘」，例如 08:30 → 510
            min(hour(ts) * 60 + minute(ts)) FILTER (activity = 'Logon')   AS first_logon_min,
            max(hour(ts) * 60 + minute(ts)) FILTER (activity = 'Logoff')  AS last_logoff_min,
            count(DISTINCT pc)                                            AS n_pc,
            -- 登入「不是自己的電腦」幾次（情境 3：登入主管電腦）
            count(*) FILTER (activity = 'Logon' AND main_pc IS NOT NULL
                             AND pc <> main_pc)                           AS other_pc_logon_cnt
        FROM t
        GROUP BY ALL
    """
    return save(sql, 'logon')


# ── 2. device：USB 插拔 ───────────────────────────────────
def device():
    sql = f"""
        WITH t AS (SELECT user, activity, {TS} AS ts FROM {read_csv('device.csv')})
        SELECT
            user AS user_id,
            CAST(ts AS DATE)                                          AS date,
            count(*) FILTER (activity = 'Connect')                    AS usb_cnt,
            count(*) FILTER (activity = 'Connect' AND {AFTER_HOURS})  AS ah_usb_cnt
        FROM t
        GROUP BY ALL
    """
    return save(sql, 'device')


# ── 3. file：複製檔案到 USB ───────────────────────────────
# 每一筆都是「把檔案複製到隨身碟」
def file():
    sql = f"""
        WITH t AS (SELECT user, filename, {TS} AS ts FROM {read_csv('file.csv')})
        SELECT
            user AS user_id,
            CAST(ts AS DATE)                                        AS date,
            count(*)                                                AS file_cnt,
            count(*) FILTER ({AFTER_HOURS})                         AS ah_file_cnt,
            -- 執行檔（情境 3：用 USB 帶鍵盤側錄程式）
            count(*) FILTER (lower(filename) LIKE '%.exe')          AS exe_file_cnt
        FROM t
        GROUP BY ALL
    """
    return save(sql, 'file')


# ── 4. email：寄信 ────────────────────────────────────────
def email():
    # 附件欄位名稱在不同說明裡寫法不同（attachments / attachment_count），自動判斷
    header = (RAW / 'email.csv').open(encoding='utf-8').readline().strip().split(',')
    att = 'attachments' if 'attachments' in header else 'attachment_count'

    sql = f"""
        WITH t AS (
            SELECT
                user, {TS} AS ts,
                TRY_CAST("{att}" AS INTEGER) AS att_cnt,
                -- 把 to / cc / bcc 合併後拆成一個一個收件人
                list_filter(
                    string_split(concat_ws(';', "to", cc, bcc), ';'),
                    x -> trim(x) <> ''
                ) AS rcpts
            FROM {read_csv('email.csv')}
        )
        SELECT
            user AS user_id,
            CAST(ts AS DATE)                    AS date,
            count(*)                            AS email_cnt,
            count(*) FILTER ({AFTER_HOURS})     AS ah_email_cnt,
            -- 外部收件人：不是公司信箱 @dtaa.com
            sum(len(list_filter(rcpts, x -> NOT x LIKE '%@dtaa.com')))  AS ext_rcpt_cnt,
            -- 單封信最多寄給幾個人（情境 3：大量寄出恐慌信）
            max(len(rcpts))                     AS max_rcpt_cnt,
            sum(att_cnt)                        AS attach_cnt
        FROM t
        GROUP BY ALL
    """
    return save(sql, 'email')


# ── 5. http：上網 ─────────────────────────────────────────
# 網域分類沿用第一部分 http_slim.sql，之後看資料再擴充
def http():
    sql = f"""
        WITH t AS (
            SELECT
                user, {TS} AS ts, lower(url) AS url,
                lower(regexp_extract(url, '://([^/]+)', 1)) AS domain
            FROM {read_csv('http.csv')}
        )
        SELECT
            user AS user_id,
            CAST(ts AS DATE)                    AS date,
            count(*)                            AS http_cnt,
            count(*) FILTER ({AFTER_HOURS})     AS ah_http_cnt,
            count(DISTINCT domain)              AS n_domain,
            -- 情境 1：上傳到 wikileaks
            count(*) FILTER (domain LIKE '%wikileaks%')                 AS leak_cnt,
            -- 情境 2：逛求職網站
            count(*) FILTER (domain SIMILAR TO
                '.*(linkedin|careerbuilder|monster|indeed|simplyhired|jobhuntersbible|job-hunt)\\..*')
                                                AS job_cnt,
            -- 雲端／檔案分享
            count(*) FILTER (domain SIMILAR TO
                '.*(dropbox|mediafire|mega|4shared|box)\\..*')          AS cloud_cnt,
            -- 情境 3：下載鍵盤側錄程式
            count(*) FILTER (url LIKE '%keylog%')                       AS keylog_cnt
        FROM t
        GROUP BY ALL
    """
    return save(sql, 'http')


# ── 主程式 ────────────────────────────────────────────────
STEPS = {'logon': logon, 'device': device, 'file': file, 'email': email, 'http': http}

if __name__ == '__main__':
    todo = sys.argv[1:] or list(STEPS)   # 沒指定就全部跑，順序由小到大
    for name in todo:
        t0 = time.time()
        print(f'▶ {name} 處理中…', flush=True)
        path = STEPS[name]()
        # 檢查結果：幾列、幾個人、日期範圍
        rows, users, d0, d1 = con.execute(
            f"SELECT count(*), count(DISTINCT user_id), min(date), max(date) FROM '{path}'"
        ).fetchone()
        print(f'  完成 {time.time() - t0:.0f} 秒｜{rows:,} 列｜{users} 人｜{d0} ~ {d1}')
        print(con.execute(f"SELECT * FROM '{path}' LIMIT 3").df().to_string(), '\n')
