select
    unique_key                                     as request_id,
    created_date,
    closed_date,
    agency,
    complaint_type,
    descriptor,
    incident_zip,
    status,
    borough,
    date(created_date)                             as created_day,
    date_diff('hour', created_date, closed_date)   as hours_to_close
from {{ source('nyc311', 'requests') }}