-- Share of requests with an official SLA. Below 85% the compliance numbers stop describing most of 311.
{{ config(severity='warn') }}
select coverage
from (
    select avg(if(sla_outcome = 'no_sla', 0.0, 1.0)) as coverage
    from {{ ref('fct_service_requests') }}
)
where coverage < 0.85
