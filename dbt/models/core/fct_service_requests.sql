-- One row per service request, with its SLA target and whether it met it as of var('as_of_date').
--
-- sla_outcome:
--   met / missed   closed, and closed within / after the SLA
--   missed_open    still open, but already older than the SLA: it can no longer meet it
--   pending        still open and not yet past the SLA: too early to judge
--   no_sla         no official SLA for this complaint type
--   not_tracked    the agency never closes this complaint type (see closure_tracking below)
--   invalid        closed before created, or status Closed with no close date
--
-- Partitions were ingested on different days. To compare them on one footing, every request is
-- viewed as of var('as_of_date'): a close after that moment is treated as not yet closed.

{% set as_of = "timestamp '" ~ var('as_of_date') ~ " 00:00:00'" %}

with requests as (
    select * from {{ ref('stg_311_requests') }}
),

sla_exact as (
    select complaint_type, descriptor, sla_hours
    from {{ ref('stg_sla_targets') }}
    where descriptor is not null
),

sla_by_type as (                                   -- fallback: longest SLA for the complaint type
    select complaint_type, max(sla_hours) as sla_hours
    from {{ ref('stg_sla_targets') }}
    group by 1
),

joined as (
    select
        r.*,
        coalesce(e.sla_hours, t.sla_hours)                                  as sla_hours,
        case when e.sla_hours is not null then 'complaint_type+descriptor'
             when t.sla_hours is not null then 'complaint_type'
             else 'none' end                                                as sla_match_level
    from requests r
    left join sla_exact e
        on r.complaint_type_key = e.complaint_type and r.descriptor_key = e.descriptor
    left join sla_by_type t
        on r.complaint_type_key = t.complaint_type
),

as_of_view as (
    select
        *,
        if(closed_date < {{ as_of }}, closed_date)                          as closed_as_of
    from joined
    where created_date < {{ as_of }}
),

closure_tracking as (                              -- some types are logged but never closed, e.g. helicopter noise
    select agency, complaint_type
    from as_of_view
    where created_date < {{ as_of }} - interval '90' day
    group by 1, 2
    having count(*) >= 50
       and avg(if(closed_as_of is null, 1.0, 0.0)) >= 0.99
),

measured as (
    select
        *,
        date_diff('second', created_date, closed_as_of) / 3600.0            as hours_open,
        date_diff('second', created_date, {{ as_of }}) / 3600.0             as age_hours,
        not coalesce(
               closed_as_of < created_date
            or (closed_date is null and status = 'Closed'),
            false
        )                                                                   as is_valid_duration,
        exists (
            select 1 from closure_tracking c
            where c.agency = as_of_view.agency and c.complaint_type = as_of_view.complaint_type
        )                                                                   as is_never_closed_type
    from as_of_view
)

select
    request_id,
    created_date,
    closed_as_of                                                            as closed_date,
    created_day,
    date_trunc('month', created_day)                                        as created_month,
    agency,
    complaint_type,
    descriptor,
    borough,
    incident_zip,
    status                                                                  as status_at_ingest,
    closed_as_of is null                                                    as is_open,
    is_valid_duration,
    case when is_valid_duration then hours_open end                         as hours_to_close,
    sla_hours,
    sla_match_level,
    is_never_closed_type,
    case
        when not is_valid_duration           then 'invalid'
        when sla_hours is null               then 'no_sla'
        when is_never_closed_type            then 'not_tracked'
        when closed_as_of is not null        then if(hours_open <= sla_hours, 'met', 'missed')
        when age_hours > sla_hours           then 'missed_open'
        else 'pending'
    end                                                                     as sla_outcome
from measured
