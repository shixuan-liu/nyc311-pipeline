# NYC 311 Pipeline

A daily batch pipeline for NYC 311 service requests. It pulls each day's requests from the city's open-data API, lands the raw JSON in S3, converts it to typed, date-partitioned Parquet, and exposes it to Athena. dbt builds analytics tables on top, with data tests.

```
Socrata API ──ingest.py──▶ S3 raw/ (JSON) ──transform.py──▶ S3 curated/ (Parquet) ──▶ Athena table ──dbt──▶ marts
                                                                                                          ├─ complaints_daily
                                                                                                          ├─ agency_response_times
                                                                                                          └─ housing_complaints_by_zip
```

Backfilled for 2026-07-01 → 2026-09-27 (89 days). About 10,000 requests a day. One day of raw JSON is ~44.5 MB; the same day as Parquet is ~1.1 MB.

## Layout

| Path | What it does |
|---|---|
| `ingest.py` | Pulls one day from the API, page by page, into `s3://<lake>/raw/nyc311/dt=YYYY-MM-DD/` |
| `transform.py` | Reads one day of raw JSON, keeps 12 columns, casts types, removes invalid and duplicate rows, writes one Parquet file to `curated/` |
| `backfill.py` | Runs ingest + transform for a date range, one day at a time |
| `sql/create_curated_table.sql` | Athena DDL for the curated table, partitioned by `dt` |
| `dbt/models/staging/` | `stg_311_requests`: renames columns and derives `created_day` and `hours_to_close` |
| `dbt/models/marts/` | Aggregated tables for daily volume, agency response times, and HPD housing complaints by ZIP |

## Design decisions

**Raw and curated zones are kept separate.** Raw JSON is stored exactly as the API returned it. If the cleaning logic changes, curated data can be rebuilt from raw without calling the API again.

**Every run is idempotent.** Both scripts delete that day's existing files before writing. Rerunning a day replaces it instead of duplicating it, so a failed or partial day can simply be run again.

**Pagination uses a stable sort order.** Pages are requested with `$order=unique_key`. Without a fixed order, the API can return rows in a different order on each call, so offset-based pages could overlap or skip rows.

**Retries with exponential backoff.** API calls retry up to 5 times, waiting 2, 4, 8, 16 and 32 seconds, so a brief network or rate-limit error doesn't fail the whole day.

**Every run is reconciled.** Ingest compares the rows landed against the API's `count(*)` for that day. Transform asserts `raw = written + invalid + duplicates`. Rows are never dropped silently: if a number doesn't add up, the run says so.

**Parquet, partitioned by day.** Columnar storage with typed columns cuts storage about 40× and lets Athena read only the columns and days a query needs, which is what Athena bills on.

**dbt staging views, mart tables.** Staging models are views (no storage, always current). Marts are materialized as tables so dashboard queries are fast and cheap.

**Backfill logs failures instead of stopping.** A bad day is recorded and the backfill moves on. The run ends with a list of failed days to rerun.

## Data tests

- `request_id` is unique and not null.
- `borough` is one of the five boroughs or `Unspecified`.

## Finding: average resolution time is biased low

`agency_response_times` averages `hours_to_close` over closed requests only. Requests that are still open are the slow ones, and they are left out, so the average understates how long requests actually take. The bias is largest for recent days, where more requests are still open. A fairer measure would compare agencies on requests old enough to have had time to close, or use a survival-style measure that accounts for open requests.

## Known limitations and next steps

- **New partitions must be registered.** Athena does not see a new `dt=` folder until `MSCK REPAIR TABLE` is run. The next step is partition projection on the table, so new days appear automatically.
- **Negative durations.** Some source records have `closed_date` earlier than `created_date`. These should be filtered or flagged in staging, with a dbt test.
- **Offset pagination on live data.** If the city adds or edits records for a day while it is being ingested, offsets can shift. The count reconciliation detects this, and a rerun fixes it.
- **Infrastructure is not in this repo.** The S3 buckets, Athena workgroup and Glue database were created separately.

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python ingest.py --date 2026-09-20
python transform.py --date 2026-09-20
python backfill.py --start 2026-09-01 --end 2026-09-20

cd dbt && dbt build --profiles-dir .
```

Requires AWS credentials with access to the lake bucket and Athena workgroup named in the scripts and `dbt/profiles.yml`.
