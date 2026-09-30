--只保留 2010-07-20 ~ 2010-08-20 給 Power BI 匯入用

---建立view表一、收件人明細(FACT表)  粒度為一列一個收件人；目的把一欄多個收件人拆開去分析出收件人來源差異

drop table if exists [dbo].[tbl_email_recipient_0720_0820]

select
    cast(e.[id] as nvarchar(50)) as email_id,
    e.[date] as datetime,
    cast(e.[date] as date) as date,
    cast(e.[user] as nvarchar(20)) as user_id,
    cast(e.[pc] as nvarchar(20)) as pc_id,
    r.recipient_type,
    cast(LTRIM(RTRIM(s.value)) as nvarchar(200)) as recipient_email,
    case when LTRIM(RTRIM(s.value)) like '%@dtaa.com'
         then 'internal' else 'external' end as recipient_domain_type
into [dbo].[tbl_email_recipient_0720_0820]
from [dbo].[email] e
cross apply (
    select 'to' as recipient_type, e.[to] as recipient_list
    union all select 'cc', e.[cc]
    union all select 'bcc', e.[bcc]
) r
cross apply string_split(r.recipient_list, ';') s
where e.[date] >= '2010-07-20' and e.[date] < '2010-08-21'   -- 先篩日期，後面的拆字才會快
  and LTRIM(RTRIM(s.value)) <> ''

create clustered index IX_email_recipient_0720_0820
on [dbo].[tbl_email_recipient_0720_0820] (email_id)
go

---建立view表二、信件內容(FACT表) 粒度為一列一封信；目的去看信件的內容(時間、大小、附件)
--由於此資料集信件content為不是「真的信件內容」，是隨機英文單字堆疊故不在此次分析範圍
drop table if exists [dbo].[tbl_fact_email_0720_0820]

select
    cast(e.[id] as nvarchar(50)) as email_id,
    e.[date] as datetime,
    cast(e.[date] as date) as date,
    cast(e.[user] as nvarchar(20)) as user_id,
    cast(e.[pc] as nvarchar(20)) as pc_id,
    cast(e.[from] as nvarchar(200)) as from_email,
    e.[size],
    e.[attachments] as attachment_count,
    datepart(hour, e.[date]) as email_hour,
    case when datepart(hour, e.[date]) between 6 and 20
         then 'normal' else 'abnormal' end as logtime_condition,
    case when datepart(weekday, e.[date]) in (1,7)
         then 'weekend' else 'weekday' end as day_type,
    isnull(r.total_recipients, 0) as total_recipients,
    isnull(r.external_recipients, 0) as external_recipients,
    isnull(r.has_bcc_external, 0) as has_bcc_external
into [dbo].[tbl_fact_email_0720_0820]
from [dbo].[email] e
left join (
    select
        email_id,
        count(*) as total_recipients,
        sum(case when recipient_domain_type = 'external' then 1 else 0 end) as external_recipients,
        max(case when recipient_type = 'bcc' and recipient_domain_type = 'external' then 1 else 0 end) as has_bcc_external
    from [dbo].[tbl_email_recipient_0720_0820]
    group by email_id
) r on r.email_id = cast(e.[id] as nvarchar(50))
where e.[date] >= '2010-07-20' and e.[date] < '2010-08-21'

create clustered index IX_fact_email_0720_0820
on [dbo].[tbl_fact_email_0720_0820] (date, user_id)
go

--建立view表三、一人一天的寄件狀況   粒度以人/天為單位彙總； 
--若以單一封信去看很難看出異常，若以一人一天寄件量可以看出差異

drop table if exists [dbo].[tbl_agg_email_daily_0720_0820]

select
    user_id,
    date as log_date,
    count(*) as email_count,
    sum(attachment_count) as total_attachments,
    sum(cast(size as bigint)) as total_size,
    sum(case when logtime_condition = 'abnormal' then 1 else 0 end) as abnormal_time_count,
    sum(case when day_type = 'weekend' then 1 else 0 end) as weekend_count,
    sum(external_recipients) as total_external_recipients,
    sum(has_bcc_external) as bcc_external_count
into [dbo].[tbl_agg_email_daily_0720_0820]
from [dbo].[tbl_fact_email_0720_0820]
group by user_id, date

create clustered index IX_agg_email_daily_0720_0820
on [dbo].[tbl_agg_email_daily_0720_0820] (log_date, user_id)
go

--檢查筆數
select 'recipient' as tbl, count(*) as rows_ from [dbo].[tbl_email_recipient_0720_0820]
union all select 'fact', count(*) from [dbo].[tbl_fact_email_0720_0820]
union all select 'agg_daily', count(*) from [dbo].[tbl_agg_email_daily_0720_0820]
