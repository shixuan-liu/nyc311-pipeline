"""Pull one day of NYC 311 service requests and land the raw JSON in S3.

Usage:
    python ingest.py --date 2026-09-20
"""
import argparse
import json
import time

import boto3
import requests

API_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
LAKE_BUCKET = "nyc311-aws-data-pipeline-lake-20260828234243378000000001"
PAGE_SIZE = 5000
MAX_RETRIES = 5

s3 = boto3.client("s3")


def get_json(params: dict) -> list[dict]:
    """Call the API, retrying with exponential backoff on failure."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(API_URL, params=params, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as err:
            wait = 2 ** attempt                                # 2, 4, 8, 16, 32 seconds
            print(f"  attempt {attempt} failed ({err}); retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"gave up after {MAX_RETRIES} attempts")


def day_filter(day: str) -> str:
    return f"created_date between '{day}T00:00:00' and '{day}T23:59:59'"


def fetch_page(day: str, offset: int) -> list[dict]:
    return get_json({
        "$where": day_filter(day),
        "$order": "unique_key",                                # stable order: pages never overlap or skip rows
        "$limit": PAGE_SIZE,
        "$offset": offset,
    })


def source_count(day: str) -> int:
    result = get_json({"$where": day_filter(day), "$select": "count(*)"})
    return int(result[0]["count"])                             # the API returns the count as a string


def clear_day(prefix: str) -> None:
    """Delete this day's existing raw files, so a rerun replaces them instead of duplicating."""
    listed = s3.list_objects_v2(Bucket=LAKE_BUCKET, Prefix=prefix)
    keys = [{"Key": obj["Key"]} for obj in listed.get("Contents", [])]
    if keys:
        s3.delete_objects(Bucket=LAKE_BUCKET, Delete={"Objects": keys})
        print(f"  removed {len(keys)} old file(s) under {prefix}")


def ingest_day(day: str) -> None:
    prefix = f"raw/nyc311/dt={day}/"
    clear_day(prefix)

    offset, page_no, total = 0, 0, 0
    while True:
        rows = fetch_page(day, offset)
        if not rows:
            break

        key = f"{prefix}page_{page_no:03d}.json"
        s3.put_object(Bucket=LAKE_BUCKET, Key=key, Body=json.dumps(rows))
        print(f"  page {page_no}: {len(rows)} rows -> s3://{LAKE_BUCKET}/{key}")

        total += len(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        page_no += 1

    expected = source_count(day)
    if total == expected:
        print(f"{day}: {total} rows landed in raw — matches the source count")
    else:
        print(f"WARNING {day}: landed {total} rows but the source reports {expected}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="day to ingest, YYYY-MM-DD")
    args = parser.parse_args()
    ingest_day(args.date)