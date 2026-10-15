CREATE EXTERNAL TABLE IF NOT EXISTS nyc311_analytics.requests (
  unique_key     bigint,
  created_date   timestamp,
  closed_date    timestamp,
  agency         string,
  agency_name    string,
  complaint_type string,
  descriptor     string,
  status         string,
  borough        string,
  incident_zip   string,
  latitude       double,
  longitude      double
)
PARTITIONED BY (dt string)
STORED AS PARQUET
LOCATION 's3://nyc311-aws-data-pipeline-lake-20260828234243378000000001/curated/nyc311/'
-- Partition projection: Athena derives the dt partitions from this rule, so a newly written day is
-- queryable immediately. Without it, every new dt= folder must be registered (MSCK REPAIR TABLE).
TBLPROPERTIES (
  'projection.enabled'          = 'true',
  'projection.dt.type'          = 'date',
  'projection.dt.format'        = 'yyyy-MM-dd',
  'projection.dt.range'         = '2026-01-01,NOW',
  'projection.dt.interval'      = '1',
  'projection.dt.interval.unit' = 'DAYS',
  'storage.location.template'   = 's3://nyc311-aws-data-pipeline-lake-20260828234243378000000001/curated/nyc311/dt=${dt}/'
);
