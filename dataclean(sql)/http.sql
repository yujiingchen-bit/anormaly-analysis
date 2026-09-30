--查看 前20筆資料型態

select top 20 * from [dbo].[http]

--建立view表  一天一人一PC的瀏覽明細
alter view [dbo].[view_fact_http] as 
select [date] as datetime,cast([date] as date) as date,round(datepart(hour,[date])+datepart(minute,[date])/60.0+datepart(second,[date])/3600.0,1) as time,[user] as user_id,
pc as pc_id,    
lower(substring([url],charindex('//', [url]) + 2,charindex('/', [url] + '/', charindex('//', [url]) + 2) - charindex('//', [url]) - 2 )) as domain
from [dbo].[http]

--建立view表  彙總一天一人上網次數(以天為單位)

alter view [dbo].[view_agg_http_count] as 
select    user_id, date,count(*) as visit_count,
    count(distinct [pc_id]) as unique_pc_count,
    sum(case when datepart(hour, [datetime]) not between 6 and 20 then 1 else 0 end) as abnormal_time_count,
    sum(case when datepart(weekday, [datetime]) in (1,7) then 1 else 0 end) as weekend_count
from [dbo].[view_fact_http] 
group by  user_id, date



--查看view表
select top 20 * from [dbo].[view_fact_http]
select top 20 * from [dbo].[view_agg_http_count] 



