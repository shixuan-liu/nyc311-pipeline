select  incident_zip,
        complaint_type,
        count(*) as requests

from {{ ref('stg_311_requests') }}
where agency='HPD'
group by incident_zip, complaint_type
