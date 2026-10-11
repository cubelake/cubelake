# apple-itunes

iTunes lookup for every app charted by apple-rss → bronze JSON → `silver_itunes_app_details`.
Independent service: own config, storage helpers, dbt project, Airflow DAG and image.

## CLI

| Command | What it does |
|---|---|
| `apple-itunes extract --date D` | read app ids from apple-rss silver for D, look them up, write bronze JSON |
| `apple-itunes pending --stage extract\|transform` | print (last line, JSON) dates still to process |
| `apple-itunes transform --date D` | dbt `+silver_itunes_app_details` → `$APPLE_ITUNES_SILVER_URI/snapshot_date=D/app_details.parquet` |

## Configuration

| Env var | Example |
|---|---|
| `APPLE_ITUNES_RSS_SILVER_URI` | input: `gs://cubelake-silver/appstore_rss` |
| `APPLE_ITUNES_BRONZE_URI` | `gs://cubelake-bronze/appstore_itunes` |
| `APPLE_ITUNES_SILVER_URI` | `gs://cubelake-silver/appstore_itunes` |
| `APPLE_ITUNES_GCS_HMAC_KEY_ID`, `APPLE_ITUNES_GCS_HMAC_SECRET` | only for `gs://` (DuckDB in dbt) |

## Contract

Triggered by asset `apple_rss_silver`; publishes `apple_itunes_silver`. Consumed by appstore-analytics.

## Develop

```bash
uv sync && uv run pytest
docker build -t apple-itunes:local .
```
