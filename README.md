# Cubelake

> Data engineering platform for collecting, processing, and analyzing Apple App Store data.

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![Airflow](https://img.shields.io/badge/Apache_Airflow-3.3-017CEE?logo=apacheairflow&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-1.10+-FF694B?logo=dbt&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-1.2+-FFF000?logo=duckdb&logoColor=black)
![License](https://img.shields.io/badge/License-MIT-green)

Cubelake is a **medallion lake** (bronze → silver → gold) built from **independent ELT services**,
one per data source, each in its own repository. A service owns everything about its source —
HTTP collection, storage paths, bronze format, dbt models, Airflow DAG, Dockerfile, tests and
dependencies. Services share no code; they talk only through datasets in the lake, and those
datasets are defined by versioned **data contracts**.

This repository is only the **project overview**. All code lives in the repos below.

## Repositories

| Repo | Role |
| --- | --- |
| [`apple-rss`](https://github.com/Cubelake/apple-rss) | Apple RSS top charts → bronze → `silver_top_apps` |
| [`apple-itunes`](https://github.com/Cubelake/apple-itunes) | iTunes lookup for charted apps → bronze → `silver_itunes_app_details` |
| [`appstore-analytics`](https://github.com/Cubelake/appstore-analytics) | joins both silvers → `silver_appstore_apps` → gold marts |
| [`cubelake-contracts`](https://github.com/Cubelake/cubelake-contracts) | ODCS data contracts for every published dataset + parquet checker |
| [`cubelake-platform`](https://github.com/Cubelake/cubelake-platform) | Airflow runtime (docker compose); later Terraform for GCP and deploys |

## Data flow

```text
apple-rss (@daily)
  extract ─► bronze/appstore_rss/snapshot_date=D/*.json
  transform (dbt) ─► silver/appstore_rss/…/top_apps.parquet          contract apple_rss.silver_top_apps
                                                                       asset apple_rss_silver
apple-itunes (on apple_rss_silver)
  extract ─► bronze/appstore_itunes/snapshot_date=D/*.json
  transform (dbt) ─► silver/appstore_itunes/…/app_details.parquet    contract apple_itunes.silver_itunes_app_details
                                                                       asset apple_itunes_silver
appstore-analytics (on both silvers)
  silver ─► silver/appstore/…/apps.parquet
  gold-daily ─► gold/fct_top_apps, gold/fct_genre_stats
  dim-apps ─► gold/dim_apps                                            asset appstore_gold
appstore_rank_history (1st & 15th) ─► gold/fct_app_rank_history
```

Every step that works on dates first asks the service which days are **pending** (input exists,
output doesn't), so missed days and backfills are picked up automatically.

## Getting started

Prerequisites: [uv](https://docs.astral.sh/uv/), [just](https://github.com/casey/just), Docker.
Keep all repos side by side:

```bash
mkdir cubelake-workspace && cd cubelake-workspace
git clone https://github.com/Cubelake/cubelake-platform.git
cd cubelake-platform
just clone      # apple-rss, apple-itunes, appstore-analytics, cubelake-contracts next to it
just test-all
just init && just up   # Airflow on http://localhost:8080
```

Each service also runs on its own — see its README (`uv sync && uv run pytest`, `uv run <service> --help`).

## Known limitations

- **Cloud is not wired yet.** Every service supports `gs://` paths, but GCS, Terraform and CD come after the GCP project exists.
- **Contracts are not enforced in the services yet** — that needs the contracts repo published so services can pin a tag.
- **`gold_fct_app_rank_history`** is a full recompute every run.
- **Images are large (~1.4 GB)** because of dbt + Google client libraries.
- **No CI yet.**

## License

[MIT](LICENSE)
