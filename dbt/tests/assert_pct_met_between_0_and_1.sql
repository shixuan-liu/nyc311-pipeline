select * from {{ ref('mart_sla_compliance') }}
where pct_met < 0 or pct_met > 1 or pct_decided < 0 or pct_decided > 1
