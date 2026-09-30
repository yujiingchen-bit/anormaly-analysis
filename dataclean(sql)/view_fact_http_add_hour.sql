--在 view_fact_http 補一個整數小時欄位 hour_of_day (0~23)
--用途：Power BI 畫「24小時上網次數分布」長條圖，X軸要用整數，不能用有小數的 time

use [insider-threat-behavior]
go

alter view [dbo].[view_fact_http] as
select
    [date] as datetime,
    cast([date] as date) as date,
    round(datepart(hour,[date]) + datepart(minute,[date])/60.0 + datepart(second,[date])/3600.0, 1) as time,
    datepart(hour, [date]) as hour_of_day,      -- 新增：整數小時 0~23，畫長條圖專用
    [user] as user_id,
    pc as pc_id,
    lower(substring([url], charindex('//', [url]) + 2,
         charindex('/', [url] + '/', charindex('//', [url]) + 2) - charindex('//', [url]) - 2)) as domain
from [dbo].[http]
go

select top 5 hour_of_day, time from [dbo].[view_fact_http]
