--紀錄裝置(usb)插拔的狀況與時間
--算是維度表  
--一位user多台電腦 顆粒度以一台pc為單位
--查看前20筆

select top 20 * from [dbo].[device]


--確認id的意義 為PK值與其他表無關連 view表可移除
select count(*) from [dbo].[device]
select count(distinct [id]) from [dbo].[device]


--建立view表
create view [dbo].[view_dim_userpc] as
select [date],[user] as 'user_id',[pc] as 'pc_id',[activity] as 'device_activity' from [dbo].[device]

--建立view表  粒度每人每天插拔裝置次數
create view [dbo].[view_fact_device_count] as
select user_id,pc_id,cast([date] as date) as device_date,
sum(case when [device_activity]='Connect' then 1 else 0 end ) as connect_count,
sum(case when [device_activity]='Disconnect' then 1 else 0 end ) as Disconnect_count
from [dbo].[view_dim_userpc] 
group by user_id,pc_id,cast([date] as date)


--查看view表
select top 10 * from  [dbo].[view_dim_userpc] 
select top 10 * from  [dbo].[view_fact_device_count]