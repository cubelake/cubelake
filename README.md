# appstore-transform

> dbt-duckdb project implementing the silver and gold layers of the [Cubelake](https://github.com/Cubelake/cubelake) medallion pipeline.

![dbt](https://img.shields.io/badge/dbt--duckdb-1.10+-FF694B?logo=dbt&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-in--process-FFF000?logo=duckdb&logoColor=black)
![Azure](https://img.shields.io/badge/Azure_ADLS_Gen2-0078D4?logo=microsoftazure&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

DuckDB reads bronze JSON and silver/gold Parquet directly off Azure Data Lake Storage Gen2 (`azure://` paths) — there's no persistent warehouse; every model materializes straight back to ADLS. Invoked by the silver/gold DAGs in [`appstore-dags`](https://github.com/Cubelake/appstore-dags).

---

## Models

```
models/
├── staging/
│   ├── apple_rss/stg_bronze_top_apps.sql          # unnest bronze RSS JSON, derive chart rank from array position
│   └── apple_itunes/stg_bronze_itunes.sql         # unnest bronze iTunes JSON against an explicit ~29-field struct schema
└── marts/
    ├── apple_rss/silver_top_apps.sql              # cleaned RSS chart rows              → silver/appstore_rss/snapshot_date=.../top_apps.parquet
    ├── apple_itunes/silver_itunes_app_details.sql # cleaned iTunes metadata              → silver/appstore_itunes/snapshot_date=.../app_details.parquet
    ├── appstore/silver_appstore_apps.sql           # RSS ⋈ iTunes on (app_id, country, snapshot_date) → silver/appstore/snapshot_date=.../apps.parquet
    └── gold/
        ├── gold_fct_top_apps.sql                  # daily chart-position fact            → gold/fct_top_apps/snapshot_date=.../data.parquet
        ├── gold_fct_genre_stats.sql                # daily per-genre aggregates + #1 app  → gold/fct_genre_stats/snapshot_date=.../data.parquet
        ├── gold_dim_apps.sql                       # SCD Type 1 app dimension (latest known state per app_id) → gold/dim_apps/data.parquet
        └── gold_fct_app_rank_history.sql           # full-history rank/streak fact        → gold/fct_app_rank_history/data.parquet
```

All staging models are `materialized='table'` (in DuckDB's in-memory catalog); every mart/gold model overrides this with `materialized='external', format='parquet'` and an explicit `azure://` `location`.

## Azure secrets

`dbt_project.yml`'s `on-run-start` hooks create DuckDB `CREATE OR REPLACE SECRET` statements before every run, one per container/prefix (DuckDB matches the most specific prefix, so `silver_rss_secret`/`silver_itunes_secret` override the generic `silver_secret` for their sub-paths):

| Secret | Scope | Env vars |
|---|---|---|
| `bronze_secret` | `azure://bronze` | `ACCOUNT_NAME`, `BRONZE_SAS_TOKEN` |
| `silver_secret` | `azure://silver` | `ACCOUNT_NAME`, `SILVER_SAS_TOKEN` |
| `silver_rss_secret` | `azure://silver/appstore_rss` | `ACCOUNT_NAME`, `SILVER_RSS_SAS_TOKEN` |
| `silver_itunes_secret` | `azure://silver/appstore_itunes` | `ACCOUNT_NAME`, `SILVER_ITUNES_SAS_TOKEN` |
| `gold_secret` | `azure://gold` | `ACCOUNT_NAME`, `GOLD_SAS_TOKEN` |

`azure://silver/appstore/...` (read/written by `silver_appstore_apps` and every gold model) has no dedicated secret and falls back to `silver_secret`. Missing token env vars default to an empty string rather than failing the hook, so an unset token surfaces as an Azure auth error at query time, not at startup.

## Running locally

```bash
# from the cubelake workspace root
uv run --env-file .env dbt debug --project-dir appstore-transform

uv run --env-file .env dbt run --project-dir appstore-transform \
  --vars '{"snapshot_date": "2026-07-24"}'

uv run --env-file .env dbt run --project-dir appstore-transform --select marts/gold
```

`snapshot_date` has no project-level default — every model except `gold_dim_apps` and `gold_fct_app_rank_history` (which glob `snapshot_date=*` across all history) requires it to be passed explicitly.

`profiles.yml` is gitignored (contains no secrets itself, but is environment-specific); create one at the project root:

```yaml
appstore_transform:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: ":memory:"
      extensions:
        - azure
        - httpfs
      settings:
        azure_transport_option_type: "curl"
        ca_cert_file: "/etc/ssl/certs/ca-certificates.crt"
```

## Known limitations

This project is intentionally minimal — the following are open items rather than oversights:

- **No `schema.yml` / dbt tests.** No model or column descriptions, no `not_null`/`unique`/`relationships` tests exist yet. A natural next step would be composite-key tests (`app_id`, `country`, `feed_type`, `snapshot_date`) on the silver/gold marts.
- **No macros.** The `feed_type` normalization pattern (`LIKE '%paid%'` / `'%free%'`) is duplicated verbatim in `silver_top_apps.sql` and `silver_itunes_app_details.sql`.
- **Partial `ref()` lineage.** Staging → silver-RSS and staging → silver-iTunes use `{{ ref() }}` correctly, but `silver_appstore_apps` and every gold model read directly via `read_parquet('azure://...')` glob paths instead of `ref()`/`source()`. `dbt docs generate` will show an incomplete DAG past the RSS/iTunes silver layer — execution order for those models is enforced by the calling Airflow DAGs, not by dbt.
- **`gold_fct_app_rank_history` is not a dbt-incremental model.** It's documented elsewhere as running "incrementally" biweekly and "full-refresh" monthly, but the SQL always does a full `snapshot_date=*` glob + recompute — there's no `materialized='incremental'`, `is_incremental()`, or `unique_key`. The biweekly/monthly cadence is purely an orchestration-level scheduling choice in `appstore-dags`, not dbt materialization behavior.

## License

[MIT](LICENSE)
