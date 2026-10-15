-- SLA compliance per agency × complaint type × month the requests were created.
--
-- pct_met is measured over decided requests only: closed ones, plus open ones already past their SLA
-- (counted as misses, so slow requests can't drop out of the average). Requests still inside their SLA
-- are pending; a month is safe to read once pct_decided is close to 1.

with monthly as (
    select
        agency,
        complaint_type,
        created_month,
        count(*)                                                                   as requests,
        count_if(sla_outcome in ('met', 'missed', 'missed_open', 'pending'))       as with_sla,
        count_if(sla_outcome in ('met', 'missed', 'missed_open'))                  as decided,
        count_if(sla_outcome = 'met')                                              as met,
        count_if(sla_outcome = 'missed_open')                                      as open_past_sla,
        count_if(sla_outcome = 'invalid')                                          as invalid,
        count_if(sla_outcome = 'not_tracked')                                      as not_tracked,
        approx_percentile(hours_to_close, 0.5) filter (where not is_open)          as median_hours_to_close
    from {{ ref('fct_service_requests') }}
    group by 1, 2, 3
),

rates as (
    select
        *,
        cast(met as double) / nullif(decided, 0)                                   as pct_met,
        cast(decided as double) / nullif(with_sla, 0)                              as pct_decided
    from monthly
)

select
    *,
    pct_met - lag(pct_met) over (
        partition by agency, complaint_type order by created_month
    )                                                                              as pct_met_change
from rates
