--copy檔案的狀態

select top 20 * from [dbo].[file]


--查看不重複檔案類型
select distinct SUBSTRING([filename],charindex('.',[filename])+1,len([filename])) from [dbo].[file]

--擷取檔案開頭前兩位content
select top 20 left([content],2) from  [dbo].[file]

--view表建立  將正常檔案類型與其header做比對 建立check_status標籤

create view [dbo].[view_fact_file] as
select  [date], [user] as [user_id],[pc] as [pc_id],SUBSTRING([filename], CHARINDEX('.', [filename]) + 1, LEN([filename]))as [filetype],
    left([content], 2) as [file_content_header]
from  [dbo].[file]

create view [dbo].[view_fact_file2] as
select  *,
case
         when [filetype] = 'doc' and [file_content_header] = 'D0' then '正常'
         when [filetype] = 'pdf' and  [file_content_header] = '25' then '正常'
         when [filetype] = 'jpg' and  [file_content_header] = 'FF' then '正常'
         when [filetype] = 'zip' and  [file_content_header] = '50' then '正常'
         when [filetype] = 'exe' and  [file_content_header] = '4D' then '正常'
         when [filetype] = 'txt' and  ([file_content_header] = 'EF' or [file_content_header] not in ('D0', '25', 'FF', '50', '4D')) THEN '正常'
       else '異常' end as  [check_status]
from  [dbo].[view_fact_file]

--view表建立  粒度每人每日file copy次數

create view [dbo].[view_fact__file_count] as
select user_id,pc_id,cast([date] as date) as copy_date,count(*) as copy_count
from [dbo].[view_fact_file2]
group by user_id,pc_id,cast([date] as date)




--查看view表
select top 10 * from  [dbo].[view_fact_file2]
select top 10 * from   [dbo].[view_fact_count]
