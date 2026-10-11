# apple-rss

Apple RSS top charts (top-free / top-paid, 100 apps, 175 countries) → bronze JSON → `silver_top_apps`.
Independent service: own config, storage helpers, dbt project, Airflow DAG and image.

## CLI

| Command | What it does |
|---|---|
| `apple-rss extract --date D` | fetch every chart, write `$APPLE_RSS_BRONZE_URI/snapshot_date=D/<country>_<feed>.json` |
| `apple-rss pending` | print (last line, JSON) bronze dates without silver output |
| `apple-rss transform --date D` | dbt `+silver_top_apps` → `$APPLE_RSS_SILVER_URI/snapshot_date=D/top_apps.parquet` |

## Configuration

| Env var | Example |
|---|---|
| `APPLE_RSS_BRONZE_URI` | `/lake/bronze/appstore_rss` or `gs://cubelake-bronze/appstore_rss` |
| `APPLE_RSS_SILVER_URI` | `/lake/silver/appstore_rss` or `gs://cubelake-silver/appstore_rss` |
| `APPLE_RSS_GCS_HMAC_KEY_ID`, `APPLE_RSS_GCS_HMAC_SECRET` | only for `gs://` (DuckDB in dbt) |

## Contract

Publishes Airflow asset `apple_rss_silver` and the parquet at `APPLE_RSS_SILVER_URI`
(`snapshot_date, app_rank, country, feed_type, app_id, app_name, …`). Consumed by apple-itunes and appstore-analytics.

## Develop

```bash
uv sync && uv run pytest
docker build -t apple-rss:local .
```

`dags/apple_rss.py` is mounted into Airflow by the cubelake platform repo.
