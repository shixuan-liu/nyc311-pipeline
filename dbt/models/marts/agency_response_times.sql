select
    agency,
    count(*)                       as closed_requests,
    round(avg(hours_to_close), 1)  as avg_hours_to_close
from {{ ref('stg_311_requests') }}
where closed_date is not null
group by agency