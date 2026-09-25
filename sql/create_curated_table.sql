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
LOCATION 's3://nyc311-aws-data-pipeline-lake-20260828234243378000000001/curated/nyc311/';