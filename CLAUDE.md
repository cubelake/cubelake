# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cubelake is a data platform for Apple App Store data: a medallion lake (bronze → silver → gold) built
from **independent ELT services, one per data source, each in its own git repository**. Airflow only
orchestrates (runs service images via DockerOperator); dbt-duckdb does the transforms; storage is a
local path in dev and GCS (`gs://`) in production (GCP not provisioned yet).

## Repository layout

This repo is the **platform**. Service and contract repos are cloned into git-ignored folders by `just clone`:

| Path | Repo | Role |
| --- | --- | --- |
| `platform/airflow/` | this | docker-compose Airflow runtime (stock image, Postgres, docker-socket-proxy) |
| `services/apple-rss/` | Cubelake/apple-rss | RSS top charts → bronze → `silver_top_apps` |
| `services/apple-itunes/` | Cubelake/apple-itunes | iTunes lookup of charted apps → bronze → `silver_itunes_app_details` |
| `services/appstore-analytics/` | Cubelake/appstore-analytics | join both silvers → `silver_appstore_apps` → gold marts |
| `contracts/` | Cubelake/cubelake-contracts | ODCS YAML contracts for every published dataset + `check()` |

**Rule: services share no code.** Each has its own `config.py` (env prefix `APPLE_RSS_` /
`APPLE_ITUNES_` / `APPSTORE_ANALYTICS_`), `storage.py`, `http.py`, `bronze.py`, `dbt.py`, dbt project
with `macros/storage.sql`, DAG, Dockerfile, `uv.lock`. Duplication between services is intentional.
Services interact only through lake datasets defined in `contracts/` and Airflow assets
(`apple_rss_silver`, `apple_itunes_silver`, `appstore_gold`).

## Commands

```bash
just clone          # clone/update service + contract repos
just setup          # uv sync in each service
just test           # each service's pytest + contract tests
just images         # docker build each service

# one service
cd services/apple-rss && uv run pytest
uv run apple-rss extract --date 2026-10-11      # needs APPLE_RSS_BRONZE_URI / APPLE_RSS_SILVER_URI
uv run apple-rss pending                         # JSON list on the last stdout line
uv run apple-rss transform --date 2026-10-11

# Airflow (platform/airflow)
just airflow-init   # generate .env secrets, build images, migrate DB
just airflow-up     # http://localhost:8080
just -f platform/airflow/justfile cli dags list
```

## Service CLI pattern

Every service exposes `pending` (prints a JSON list of dates whose input exists but output doesn't, as
the **last stdout line** — DAGs read it via DockerOperator XCom) plus per-date work commands. DAGs:
`pending` → `dates_from` (skip if empty) → `DockerOperator.partial(...).expand(command=...)` → publish asset.
For local paths the service must `ensure_dir()` the output partition before dbt, because DuckDB won't
create directories.

## Conventions

- Lake paths: `<dataset_uri>/snapshot_date=YYYY-MM-DD/<file>`; bronze file per key `<country>_<feed>.json`.
  Keep the bronze record format stable (`_source`, `_ingested_at`, `_feed_type`, `country`, payload).
- dbt paths come from `{{ uri('<name>') }}` → env `<PREFIX><NAME>_URI`; never hardcode storage.
- Changing a published dataset's columns/types requires a contract version bump in `contracts/`
  (major for breaking changes).
- Secrets only in `platform/airflow/.env` (generated, git-ignored). `just secrets` creates it.
