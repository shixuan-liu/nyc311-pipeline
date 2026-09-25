"""Turn one day of raw 311 JSON into a clean, typed Parquet file in the curated zone.

Usage:
    python transform.py --date 2026-09-20
"""
import argparse
import io
import json

import boto3
import pandas as pd

LAKE_BUCKET = "nyc311-aws-data-pipeline-lake-20260828234243378000000001"

KEEP_COLUMNS = [                                               # [1]
    "unique_key", "created_date", "closed_date", "agency", "agency_name",
    "complaint_type", "descriptor", "status", "borough", "incident_zip",
    "latitude", "longitude",
]

s3 = boto3.client("s3")


def read_raw(day: str) -> pd.DataFrame:                        # [2]
    prefix = f"raw/nyc311/dt={day}/"
    listed = s3.list_objects_v2(Bucket=LAKE_BUCKET, Prefix=prefix)
    rows = []
    for obj in listed.get("Contents", []):
        body = s3.get_object(Bucket=LAKE_BUCKET, Key=obj["Key"])["Body"].read()
        rows.extend(json.loads(body))
    return pd.DataFrame(rows)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.reindex(columns=KEEP_COLUMNS)                     # [3]

    df["unique_key"] = pd.to_numeric(df["unique_key"], errors="coerce").astype("Int64")   # [4]
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["closed_date"] = pd.to_datetime(df["closed_date"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    return df


def write_curated(df: pd.DataFrame, day: str) -> str:
    prefix = f"curated/nyc311/dt={day}/"

    listed = s3.list_objects_v2(Bucket=LAKE_BUCKET, Prefix=prefix)     # [5]
    old = [{"Key": o["Key"]} for o in listed.get("Contents", [])]
    if old:
        s3.delete_objects(Bucket=LAKE_BUCKET, Delete={"Objects": old})

    buffer = io.BytesIO()                                      # [6]
    df.to_parquet(buffer, index=False)
    key = f"{prefix}part-0000.parquet"
    s3.put_object(Bucket=LAKE_BUCKET, Key=key, Body=buffer.getvalue())
    return key


def transform_day(day: str) -> None:
    raw = read_raw(day)
    df = clean(raw)

    missing_key = df["unique_key"].isna() | df["created_date"].isna()  # [7]
    invalid = int(missing_key.sum())
    df = df[~missing_key]

    before = len(df)                                           # [8]
    df = df.drop_duplicates(subset="unique_key")
    duplicates = before - len(df)

    key = write_curated(df, day)

    print(f"{day}: raw {len(raw)} = written {len(df)} + invalid {invalid} + duplicates {duplicates}")  # [9]
    assert len(raw) == len(df) + invalid + duplicates
    print(f"  -> s3://{LAKE_BUCKET}/{key}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="day to transform, YYYY-MM-DD")
    args = parser.parse_args()
    transform_day(args.date)