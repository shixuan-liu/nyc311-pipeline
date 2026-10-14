select
    created_day,
    borough,
    complaint_type,
    count(*) as requests
from {{ ref('stg_311_requests') }}
group by 1, 2, 3