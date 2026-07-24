# appstore-dags

> Apache Airflow 3.2+ DAGs orchestrating the bronze → silver → gold pipeline for the [Cubelake](https://github.com/Cubelake/cubelake) data platform.

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![Airflow](https://img.shields.io/badge/Apache_Airflow-3.2+-017CEE?logo=apacheairflow&logoColor=white)
![dbt](https://img.shields.io/badge/dbt--duckdb-1.10+-FF694B?logo=dbt&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

Nine DAGs wire together the two ingestion libraries ([`ingestion-apple-rss`](https://github.com/Cubelake/ingestion-apple-rss), [`ingestion-apple-itunes`](https://github.com/Cubelake/ingestion-apple-itunes)) and the [`appstore-transform`](https://github.com/Cubelake/appstore-transform) dbt project into a fully automated medallion pipeline, using Airflow **Assets** for lineage instead of manual scheduling.

---

## DAGs

| DAG | dag_id | Trigger | Emits (Asset) | dbt selector |
|---|---|---|---|---|
| `apple_top_daily.py` | `bronze_top_daily` | `@daily` | `BRONZE_APPSTORE_RSS` | — |
| `transform_top_daily.py` | `silver_transform_top_daily` | Asset: `BRONZE_APPSTORE_RSS` | `SILVER_APPSTORE_RSS` | `+silver_top_apps` |
| `apple_lookup_daily.py` | `bronze_itunes_lookup_daily` | Asset: `SILVER_APPSTORE_RSS` | `BRONZE_APPSTORE_ITUNES` | — |
| `transform_lookup_daily.py` | `silver_transform_itunes_lookup_daily` | Asset: `BRONZE_APPSTORE_ITUNES` | `SILVER_APPSTORE_ITUNES` | `+silver_itunes_app_details` |
| `transform_appstore_apps_daily.py` | `silver_transform_appstore_apps_daily` | Asset: `SILVER_APPSTORE_RSS` **or** `SILVER_APPSTORE_ITUNES` | `SILVER_APPSTORE_APPS` | `silver_appstore_apps` |
| `transform_gold_daily.py` | `gold_transform_daily` | Asset: `SILVER_APPSTORE_APPS` | `GOLD_APPSTORE_DAILY` | `gold_fct_top_apps gold_fct_genre_stats` |
| `transform_gold_weekly.py`* | `gold_transform_dim_apps` | Asset: `GOLD_APPSTORE_DAILY` | `GOLD_DIM_APPS` | `gold_dim_apps` |
| `transform_gold_biweekly.py` | `gold_transform_biweekly` | Cron `0 4 1,15 * *` | `GOLD_FCT_RANK_HISTORY` | `gold_fct_app_rank_history` |
| `transform_gold_monthly.py` | `gold_transform_monthly` | Cron `0 5 1 * *` | — (no outlet) | `gold_fct_app_rank_history` |

\* File and function are named `..._weekly`/`gold_transform_weekly`, but the DAG is asset-triggered (not cron) and its `dag_id` is `gold_transform_dim_apps` — a naming leftover from an earlier iteration, kept as-is to match the deployed DAG.

**Asset lineage:**

```
BRONZE_APPSTORE_RSS ──► SILVER_APPSTORE_RSS ──┬─► BRONZE_APPSTORE_ITUNES ──► SILVER_APPSTORE_ITUNES ─┐
                                              │                                                       │
                                              └───────────────────────────────────────────────────────┴─► SILVER_APPSTORE_APPS ──► GOLD_APPSTORE_DAILY ──► GOLD_DIM_APPS

gold_transform_biweekly (1st & 15th, 04:00) ──► GOLD_FCT_RANK_HISTORY
gold_transform_monthly  (1st, 05:00)        ──► (full recompute, no Asset emitted)
```

## How discovery works

Every transform DAG starts with a `discover_*` task that decides which `snapshot_date`s still need processing, then fans out with `.expand()` (up to 4 concurrent dbt subprocesses per DAG run — 1 for the iTunes bronze DAG, to respect API pacing):

- **Directory-diff discovery** (most DAGs): lists ADLS directories directly via the Azure SDK (`snapshot_date=` prefixes) and computes `upstream_dates - downstream_dates`.
- **`bronze_itunes_lookup_daily`**: queries silver RSS Parquet via DuckDB (`read_parquet('azure://silver/appstore_rss/**/*.parquet', hive_partitioning=true)`) to find dates already in silver, then diffs against existing bronze-iTunes directories.
- **`silver_transform_appstore_apps_daily`**: intersects the silver-RSS and silver-iTunes date sets (`ready = rss_dates & itunes_dates`) before diffing against what's already in `silver/appstore` — a snapshot is only joined once *both* sources are ready.

Every discovery task raises `AirflowSkipException` when there's nothing to do, so downstream tasks skip cleanly instead of running on an empty list.

## dbt invocation

Silver/gold tasks call dbt via `subprocess.run(["dbt", "run", "--select", ..., "--vars", json.dumps({"snapshot_date": ...}), "--project-dir", DBT_PROJECT_DIR, "--profiles-dir", DBT_PROJECT_DIR, "--target-path", f"/tmp/dbt_target_{snapshot_date}"])`, raising on non-zero exit. Each task uses a unique `--target-path` so concurrent `.expand()` runs don't collide. `DBT_PROJECT_DIR` defaults to `/opt/airflow/dbt/appstore-transform` (the mount path used by the Docker Compose stack in [`infra`](https://github.com/Cubelake/infra)).

## Required environment variables

Read via [`appstore-core`](https://github.com/Cubelake/appstore-core)'s Pydantic token models — no Airflow `Variable`s or `Connection`s are used:

```bash
ACCOUNT_URL=https://<storage_account>.dfs.core.windows.net
BRONZE_RSS_SAS_TOKEN=...
SILVER_RSS_SAS_TOKEN=...
BRONZE_ITUNES_SAS_TOKEN=...
SILVER_ITUNES_SAS_TOKEN=...
SILVER_APPSTORE_SAS_TOKEN=...
GOLD_SAS_TOKEN=...

# forwarded into the dbt subprocess env to satisfy appstore-transform's on-run-start secrets
BRONZE_SAS_TOKEN=...
SILVER_SAS_TOKEN=...

DBT_PROJECT_DIR=/opt/airflow/dbt/appstore-transform
```

## Running locally

See the root [`cubelake` README](https://github.com/Cubelake/cubelake#running-the-platform) for the full Docker Compose / standalone setup. In short:

```bash
cd infra/appstore-dags
docker compose up airflow-init   # first time only
docker compose up -d
```

## Known limitations

- No automated tests (`tests/` does not exist).
- `gold_transform_monthly` is tagged `full-refresh` but its dbt invocation doesn't actually pass `--full-refresh` — harmless today since every gold model is `materialized='external'` (a full recompute regardless of the flag), but worth fixing if any model ever becomes a real incremental dbt model.
- `gold_transform_monthly` declares no output Asset, so it doesn't appear in the lineage graph.

## License

[MIT](LICENSE)
