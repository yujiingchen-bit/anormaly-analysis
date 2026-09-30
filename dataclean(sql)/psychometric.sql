--心理測驗分數

--查看前20筆

select top 20 * from [dbo].[psychometric]



--建立view表
create view [dbo].[view_fact_psychometric] as
select *,sum([O]+[C]+[E]+[A]+[N]) over (partition by [user_id]) as 'total_score'
from [dbo].[psychometric]


alter  view [dbo].[view_fact_psychometric] as
select *,case when [O]>=38 then '[O]high' else '[O]low' end as '[O]_status',
case when [C]>=38 then '[C]high' else '[C]low'end as '[C]_status',
case when [E]>=38 then '[E]high' else '[E]low'end as '[E]_status',
case when [A]>=38 then '[A]high' else '[A]low'end as '[A]_status',
case when [N]>=38 then '[N]high' else '[N]low'end as '[N]_status'
from [dbo].[psychometric]


--查看view表
select * from [dbo].[view_fact_psychometric]
