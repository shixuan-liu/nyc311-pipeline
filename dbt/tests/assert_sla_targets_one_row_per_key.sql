-- The fact table joins on (complaint_type, descriptor); duplicates here would fan out requests.
select complaint_type, descriptor, count(*) as n
from {{ ref('stg_sla_targets') }}
group by 1, 2
having count(*) > 1
