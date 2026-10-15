select *
from {{ ref('stg_sla_targets') }}
where sla_hours <= 0
