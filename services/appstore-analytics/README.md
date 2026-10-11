# appstore-analytics

Joins apple-rss and apple-itunes silver into `silver_appstore_apps`, then builds the gold marts:
`gold_fct_top_apps`, `gold_fct_genre_stats` (daily), `gold_dim_apps` (SCD1), `gold_fct_app_rank_history` (full recompute).

## CLI

| Command | What it does |
|---|---|
| `appstore-analytics pending --stage silver\|gold` | print (last line, JSON) dates still to process |
| `appstore-analytics silver --date D` | join both sources for D |
| `appstore-analytics gold-daily --date D` | `fct_top_apps` + `fct_genre_stats` for D |
| `appstore-analytics dim-apps` | rebuild `dim_apps` |
| `appstore-analytics rank-history` | rebuild `fct_app_rank_history` |

## Configuration

| Env var | Example |
|---|---|
| `APPSTORE_ANALYTICS_RSS_SILVER_URI` | input: `gs://cubelake-silver/appstore_rss` |
| `APPSTORE_ANALYTICS_ITUNES_SILVER_URI` | input: `gs://cubelake-silver/appstore_itunes` |
| `APPSTORE_ANALYTICS_SILVER_URI` | `gs://cubelake-silver/appstore` |
| `APPSTORE_ANALYTICS_GOLD_URI` | `gs://cubelake-gold` |
| `APPSTORE_ANALYTICS_GCS_HMAC_KEY_ID`, `APPSTORE_ANALYTICS_GCS_HMAC_SECRET` | only for `gs://` |

## Contract

Triggered by assets `apple_rss_silver` + `apple_itunes_silver`; publishes `appstore_gold`.
DAG `appstore_rank_history` runs on the 1st and 15th.

## Develop

```bash
uv sync && uv run pytest
docker build -t appstore-analytics:local .
```
