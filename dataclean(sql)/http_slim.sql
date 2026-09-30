--http 資料整理：目的是把網址轉成「可以分析異常」的資訊
--做法跟 email/device/file 一樣：先建 fact 表（一列一次瀏覽），再彙總成 agg 表（一人一天）
--風險分類依據：archive\answers\scenarios.txt 裡真實內鬼案例會做的事
--   案例1 上傳 wikileaks.org → 外洩網站
--   案例2 瀏覽求職網站找下家 → 求職網站
--   案例5 上傳 Dropbox        → 檔案分享
--來源表 [dbo].[http] 已經是瘦身過的 2010-07-20~08-20（200萬筆），不用再篩日期

use [insider-threat-behavior]
go

--① fact 表：一列一次瀏覽，拆出網域 + 上下班時間標籤
drop table if exists [dbo].[tbl_fact_http_0720_0820]

select
    cast(h.[id] as nvarchar(50)) as http_id,
    h.[date] as datetime,
    cast(h.[date] as date) as date,
    cast(h.[user] as nvarchar(20)) as user_id,
    cast(h.[pc] as nvarchar(20)) as pc_id,
    cast(lower(substring(h.[url], patindex('%//%', h.[url]) + 2,
         charindex('/', h.[url] + '/', patindex('%//%', h.[url]) + 2) - patindex('%//%', h.[url]) - 2))
         as nvarchar(100)) as domain,
    datepart(hour, h.[date]) as visit_hour,
    case when datepart(hour, h.[date]) between 6 and 20
         then 'normal' else 'abnormal' end as logtime_condition,        -- 沿用你 logon 的做法
    case when datepart(weekday, h.[date]) in (1,7)
         then 'weekend' else 'weekday' end as day_type
into [dbo].[tbl_fact_http_0720_0820]
from [dbo].[http] h

--② 網域風險分類：清單先抓最明確的幾個，之後看資料再擴充
alter table [dbo].[tbl_fact_http_0720_0820] add risk_category nvarchar(20)
go

update [dbo].[tbl_fact_http_0720_0820]
set risk_category =
    case
        when domain like '%wikileaks%' then '外洩網站'
        when domain in ('dropbox.com','mediafire.com','mega.co.nz','4shared.com','box.com','box.net')
             then '檔案分享'
        when domain in ('linkedin.com','careerbuilder.com','monster.com','indeed.com','simplyhired.com')
             then '求職網站'
        when domain in ('gmail.com','hotmail.com','yahoo.com','inbox.com','mail.com')
             then '個人信箱'
        else '一般'
    end
go

create clustered index IX_fact_http_0720_0820
on [dbo].[tbl_fact_http_0720_0820] (date, user_id)
go

--③ agg 表：一人一天彙總，這張才是 Power BI 卡片/圖表主要接的表
drop table if exists [dbo].[tbl_agg_http_daily_0720_0820]

select
    user_id,
    date as log_date,
    count(*) as visit_count,
    count(distinct domain) as unique_domain_count,
    sum(case when logtime_condition = 'abnormal' then 1 else 0 end) as abnormal_time_count,
    sum(case when day_type = 'weekend' then 1 else 0 end) as weekend_count,
    sum(case when risk_category = '外洩網站' then 1 else 0 end) as leak_site_count,
    sum(case when risk_category = '檔案分享' then 1 else 0 end) as file_sharing_count,
    sum(case when risk_category = '求職網站' then 1 else 0 end) as job_search_count,
    sum(case when risk_category = '個人信箱' then 1 else 0 end) as webmail_count
into [dbo].[tbl_agg_http_daily_0720_0820]
from [dbo].[tbl_fact_http_0720_0820]
group by user_id, date

create clustered index IX_agg_http_daily_0720_0820
on [dbo].[tbl_agg_http_daily_0720_0820] (log_date, user_id)
go

--④ 檢查筆數 + 風險分類分布
select 'fact' as tbl, count(*) as rows_ from [dbo].[tbl_fact_http_0720_0820]
union all select 'agg_daily', count(*) from [dbo].[tbl_agg_http_daily_0720_0820]

select risk_category, count(*) as visit_count, count(distinct user_id) as user_count
from [dbo].[tbl_fact_http_0720_0820]
group by risk_category
order by visit_count desc
