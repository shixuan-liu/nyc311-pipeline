-- Official 311 SLA table (NYC Open Data cs9t-e3x8), parsed into hours.
-- One row per (complaint_type, descriptor): the official table goes one level deeper
-- ("additional details"), so we keep the longest SLA at that level to avoid over-penalising agencies.

with parsed as (
    select
        lower(trim(problem))                                              as complaint_type,
        nullif(lower(trim(problem_details)), 'n/a')                       as descriptor,
        cast(regexp_extract(sla, '^\s*([0-9.]+)', 1) as double)           as sla_amount,
        case
            when regexp_like(lower(sla), '^\s*[0-9.]+\s*hours?\s*$') then 'hour'
            when regexp_like(lower(sla), '^\s*[0-9.]+\s*days?\s*$')  then 'day'
        end                                                               as sla_unit,
        sla                                                               as sla_text
    from {{ ref('sla_official') }}
)

select
    complaint_type,
    nullif(descriptor, '')                                                as descriptor,
    max(case sla_unit when 'hour' then sla_amount
                      when 'day'  then sla_amount * 24 end)               as sla_hours
from parsed
where sla_unit is not null           -- drops "SLA not managed by ..." rows: no target to measure against
group by 1, 2
