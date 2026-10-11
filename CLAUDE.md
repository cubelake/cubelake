# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cubelake is a data engineering platform for ingesting, transforming, and analyzing Apple App Store data. It implements a **medallion architecture** (bronze → silver → gold) orchestrated by Apache Airflow, with dbt-duckdb transformations and Azure Data Lake Storage Gen2 (ADLS Gen2) as the persistence layer.

## Repository Structure

This is a **uv workspace monorepo** (former git submodules were merged in with full history via `git subtree`):

| Package | Role |
|-----------|------|
| `appstore-core` | Shared library: base ingestion class, Pydantic data models, Azure/DuckDB abstractions |
| `ingestion-apple-rss` | Async Apple RSS feed ingestion service |
| `ingestion-apple-itunes` | Async iTunes lookup API ingestion service |
| `appstore-dags` | Airflow 3.2+ DAGs (bronze / silver / gold layers) |
| `appstore-transform` | dbt project (dbt-duckdb adapter) |
| `infra` | Docker Compose stack and GitHub Actions CI |

## Commands

### Setup
```bash
git clone <repo-url>

# Install all workspace packages (plain `uv sync` installs only the empty root project)
uv sync --all-packages
```

### Testing
```bash
# All ingestion tests
uv run pytest ingestion-apple-rss/tests/ ingestion-apple-itunes/tests/ -v

# Single test file
uv run pytest ingestion-apple-rss/tests/test_url_creation.py -v
```

### dbt
```bash
# Debug connection
uv run --env-file .env dbt debug --project-dir appstore-transform

# Run all models
uv run --env-file .env dbt run --project-dir appstore-transform

# Run for a specific snapshot date
uv run --env-file .env dbt run --project-dir appstore-transform --vars '{"snapshot_date": "2025-01-01"}'

# Run only gold models
uv run --env-file .env dbt run --project-dir appstore-transform --select marts/gold

# Run dbt tests
uv run --env-file .env dbt test --project-dir appstore-transform
```

### Airflow (Docker)
```bash
cd infra/appstore-dags
docker compose up airflow-init   # first time only
docker compose up -d             # start stack (UI at http://localhost:8080)
```

## Architecture

### Data Flow

```
Apple RSS API  ──► bronze_top_daily DAG ──► ADLS: bronze/appstore_rss/snapshot_date=YYYY-MM-DD/
                                                    │
                                                    ▼
                              silver_transform_top_daily DAG (dbt: +silver_top_apps)
                                                    │
                                                    ▼
                              bronze_itunes_lookup_daily DAG ──► ADLS: bronze/appstore_itunes/
iTunes API ─────────────────────────────────────────│
                                                    ▼
                         silver_transform_itunes_lookup_daily DAG (dbt: +silver_itunes_app_details)
                                                    │
                                                    ▼
                         silver_transform_appstore_apps_daily DAG (dbt: silver_appstore_apps)
                         [triggers when BOTH silver RSS and iTunes are ready; intersects available dates]
                                                    │
                                                    ▼
                              gold_transform_daily DAG (dbt: gold_fct_top_apps, gold_fct_genre_stats)
                                                    │
                                                    ▼
                              gold_transform_dim_apps DAG (dbt: gold_dim_apps)
```

### DAG Scheduling

| DAG | Schedule | Trigger |
|-----|----------|---------|
| `bronze_top_daily` | `@daily` | Time-based |
| `silver_transform_top_daily` | Asset | `BRONZE_APPSTORE_RSS` ready |
| `bronze_itunes_lookup_daily` | Asset | `SILVER_APPSTORE_RSS` ready |
| `silver_transform_itunes_lookup_daily` | Asset | `BRONZE_APPSTORE_ITUNES` ready |
| `silver_transform_appstore_apps_daily` | Asset | Either silver asset |
| `gold_transform_daily` | Asset | `SILVER_APPSTORE_APPS` ready |
| `gold_transform_dim_apps` | Asset | `GOLD_APPSTORE_DAILY` ready |
| `gold_transform_biweekly` | `0 4 1,15 * *` | Time-based (incremental) |
| `gold_transform_monthly` | `0 5 1 * *` | Time-based (full refresh) |

### Key Design Patterns

- **Dynamic task expansion**: Silver DAGs use `.expand()` to parallelize dbt runs per unprocessed `snapshot_date` (up to 4 concurrent).
- **Hive partitioning**: Bronze data stored as `snapshot_date=YYYY-MM-DD/` in ADLS.
- **DuckDB secrets**: `dbt_project.yml` `on-run-start` hooks dynamically create DuckDB Azure secrets (`bronze_secret`, `silver_secret`, `gold_secret`, etc.) using SAS tokens from env vars before each run.
- **Airflow Asset lineage**: DAGs declare Airflow Assets as inputs/outputs — downstream DAGs trigger automatically without explicit scheduling.
- **BaseIngestor pattern**: Both ingestion services extend `appstore-core`'s `BaseIngestor` (async httpx, `batch_size=10`, `timeout=15s`, `max_retries=2`). New sources should extend this class and implement `normalize()` and `collect()`.

### appstore-core: Central Abstraction

`appstore-core/common/base_ingestor.py` is the foundation. It handles async HTTP, retry logic, and defines the interface for all ingestors. Storage abstractions (Azure token models, path builders) and all Pydantic data models (RSS, iTunes) also live here — both ingestion services and DAGs depend on this package.

### dbt Models (appstore-transform)

```
staging/
  apple_rss/stg_bronze_top_apps.sql       — unnest & clean raw JSON
  apple_itunes/stg_bronze_itunes.sql      — parse iTunes JSON

marts/
  apple_rss/silver_top_apps.sql           — top-apps Parquet per snapshot
  apple_itunes/silver_itunes_app_details.sql — metadata Parquet per snapshot
  appstore/silver_appstore_apps.sql       — joined RSS + iTunes
  gold/gold_fct_top_apps.sql             — daily chart fact
  gold/gold_fct_genre_stats.sql          — daily genre aggregates
  gold/gold_dim_apps.sql                 — app dimension (SCD Type 1)
  gold/gold_fct_app_rank_history.sql     — all-time rank history (biweekly/monthly)
```

## Environment Variables

Create a `.env` file (used by dbt and Airflow):

```bash
ACCOUNT_URL=https://<storage_account>.dfs.core.windows.net
BRONZE_SAS_TOKEN=...
BRONZE_RSS_SAS_TOKEN=...
BRONZE_ITUNES_SAS_TOKEN=...
SILVER_SAS_TOKEN=...
SILVER_RSS_SAS_TOKEN=...
SILVER_ITUNES_SAS_TOKEN=...
GOLD_SAS_TOKEN=...
DBT_PROJECT_DIR=/path/to/appstore-transform
```
