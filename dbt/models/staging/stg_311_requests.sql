select
    unique_key                                     as request_id,       -- [1]
    created_date,
    closed_date,
    agency,
    complaint_type,
    descriptor,
    status,
    borough,
    date(created_date)                             as created_day,      -- [2]
    date_diff('hour', created_date, closed_date)   as hours_to_close    -- [3]
from {{ source('nyc311', 'requests') }}                                 -- [4]