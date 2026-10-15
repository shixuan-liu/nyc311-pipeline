-- Every month from January to the as-of date must be fully loaded. Row tests (unique, not_null)
-- pass on a table with missing partitions; this catches the gap. A NYC month has 300k+ requests.
with months as (
    select m
    from unnest(sequence(date '2026-01-01',
                         date_trunc('month', date '{{ var("as_of_date") }}') - interval '1' month,
                         interval '1' month)) as t(m)
),

loaded as (
    select date_trunc('month', created_day) as m, count(*) as n
    from {{ ref('stg_311_requests') }}
    group by 1
)

select months.m, coalesce(loaded.n, 0) as n
from months
left join loaded on months.m = loaded.m
where coalesce(loaded.n, 0) < 250000
