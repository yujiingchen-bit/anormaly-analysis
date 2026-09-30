
--查看前20筆
select top 20 * from [dbo].[view_fact_logon]


--建立view表  粒度以一筆登入登出為單位  新增標籤  正常上班時間  vs 非正常上班時間

create view [dbo].[view_fact_logon] as
select *,case when datepart(hour,[date]) between 6 and 20 then 'normal' else 'abnoraml' end as logtime_condition
from [dbo].[logon]

alter view [dbo].[view_fact_logon] as
select *,datepart(hour,[date]) as 'hour',case when datepart(hour,[date]) between 6 and 20 then 'normal' else 'abnoraml' end as logtime_condition
from [dbo].[logon]

alter view [dbo].[view_fact_logon] as
select [user] as 'user_id',[pc] as 'pc_id',[date],datepart(hour,[date]) as 'loghour',[activity] as 'log_activity',case when datepart(hour,[date]) between 6 and 20 then 'normal' else 'abnoraml' end as logtime_condition
from [dbo].[logon]



--建立view表  粒度以每天每人登入登出次數為單位

create view [dbo].[view_fact_logon_count] as
select  user_id,    pc_id,    cast([date] as date) as log_date,
    sum(case when log_activity = 'Logon' then 1 else 0 end) as logon_count,
    sum(case when log_activity = 'Logoff' then 1 else 0 end) as logoff_count
from [dbo].[view_fact_logon]
group by user_id, pc_id, cast([date] as date)

--查看view表 
select * from  [dbo].[view_fact_logon]
select * from  [dbo].[view_fact_logon_count]