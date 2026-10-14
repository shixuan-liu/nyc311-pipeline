from datetime import date, timedelta

from ingest import ingest_day
from transform import transform_day
import argparse


def back_fill(start_date:str, end_date:str):
    failed = []
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    total_days = (end - start).days+1
    while start <= end:
        day_str = start.isoformat()
        try:
            ingest_day(day_str)
            transform_day(day_str)
        except Exception as err:
            print(f"FAILED {day_str}: {err}")
            failed.append(day_str)
        start = start + timedelta(days=1)
    print(f"Backfill done: {total_days} days, {len(failed)} failed: {failed}")




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="start_date to ingest, YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="end_date to ingest, YYYY-MM-DD")
    args = parser.parse_args()
    back_fill(args.start, args.end)