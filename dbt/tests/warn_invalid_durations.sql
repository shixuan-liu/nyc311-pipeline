-- Source records closed before they were created. Kept and flagged, not deleted; warn if they grow past 1%.
{{ config(severity='warn') }}
select share
from (
    select avg(if(sla_outcome = 'invalid', 1.0, 0.0)) as share
    from {{ ref('fct_service_requests') }}
)
where share > 0.01
