"""Export the SLA mart from Athena to a CSV the dashboard reads.

The dashboard reads a file in the repo rather than querying Athena, so it needs no AWS
credentials and costs nothing per view. The mart is a monthly report, so re-exporting after
each monthly dbt build keeps it current.

Usage:
    python export_mart.py
"""
import io
import time

import boto3
import pandas as pd

WORKGROUP = "nyc311-aws-data-pipeline-workgroup"
QUERY = "select * from nyc311_analytics.mart_sla_compliance"
OUT = "dashboard/data/mart_sla_compliance.csv"

athena = boto3.client("athena", region_name="us-east-1")
s3 = boto3.client("s3")


def run_query(sql: str) -> pd.DataFrame:
    qid = athena.start_query_execution(QueryString=sql, WorkGroup=WORKGROUP)["QueryExecutionId"]
    while True:
        ex = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]
        state = ex["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(1)
    if state != "SUCCEEDED":
        raise RuntimeError(f"query {state}: {ex['Status'].get('StateChangeReason')}")
    bucket, key = ex["ResultConfiguration"]["OutputLocation"].removeprefix("s3://").split("/", 1)
    return pd.read_csv(io.BytesIO(s3.get_object(Bucket=bucket, Key=key)["Body"].read()))


if __name__ == "__main__":
    df = run_query(QUERY)
    df["created_month"] = pd.to_datetime(df["created_month"]).dt.strftime("%Y-%m")
    df.sort_values(["agency", "complaint_type", "created_month"]).to_csv(OUT, index=False)
    print(f"{len(df)} rows -> {OUT}")
