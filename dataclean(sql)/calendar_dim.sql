--日期維度表：做「每日」儀表板的必備表
--用途：PBI 篩日期範圍、算「本週 vs 上週」「平日 vs 假日」都靠這張表
--之後所有 agg_daily 表（http/email/device/file/logon）都可以跟這張表關聯

use [insider-threat-behavior]
go

drop table if exists [dbo].[dim_calendar]

;with seq as (
    select 0 as n
    union all select n + 1 from seq where n < 400   -- 涵蓋一整年多一點
)
select
    cast(dateadd(day, n, '2010-07-20') as date) as [date],
    year(dateadd(day, n, '2010-07-20')) as [year],
    month(dateadd(day, n, '2010-07-20')) as [month],
    datename(month, dateadd(day, n, '2010-07-20')) as month_name,
    day(dateadd(day, n, '2010-07-20')) as [day],
    datename(weekday, dateadd(day, n, '2010-07-20')) as weekday_name,
    case when datepart(weekday, dateadd(day, n, '2010-07-20')) in (1, 7)
         then 1 else 0 end as is_weekend,
    datepart(iso_week, dateadd(day, n, '2010-07-20')) as week_of_year
into [dbo].[dim_calendar]
from seq
where dateadd(day, n, '2010-07-20') <= '2010-08-20'
option (maxrecursion 400)
go

create clustered index IX_dim_calendar on [dbo].[dim_calendar] ([date])
go

select top 5 * from [dbo].[dim_calendar]
select count(*) as 總天數 from [dbo].[dim_calendar]
