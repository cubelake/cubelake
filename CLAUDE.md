# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Cubelake ingests Apple App Store data following the Google Cloud Lakehouse medallion pattern.
Current scope: **bronze** (raw API responses, NDJSON in GCS, BigLake external tables) and **silver**
(normalized Apache Iceberg managed tables in BigQuery). Gold is out of scope for now.

Stack: Python extract → Cloud Run job; Dataform (SQLX) for raw → silver; Cloud Workflows + Cloud
Scheduler orchestrate; Terraform for all infra. No Airflow, dbt, DuckDB or VM. The GCP project does
not exist yet — cloud code is validated offline only.

## Layout and rules

- `extract/` — uv project, package `cubelake_extract`, CLI `cubelake-extract <apple-rss|apple-itunes> --date D`.
  - `core/` = http (batched async fetch with retries), bronze record format, storage writes.
  - `apple_rss/`, `apple_itunes/` = one module per source with its own `config.py` (env prefix
    `APPLE_RSS_` / `APPLE_ITUNES_`). **They must not import each other** (`uv run lint-imports`);
    `core` must not import sources.
  - Bronze record format is stable: `_source`, `_ingested_at`, `_feed_type`, `country` + payload; files
    `<country>_<feed>.json` under `snapshot_date=YYYY-MM-DD/`. Never put `snapshot_date` inside files
    (it is the hive partition key).
- Dataform project lives at the **repo root** (`workflow_settings.yaml`, `definitions/`, `includes/`) —
  managed Dataform can't use a subdirectory. Silver models are `type: "incremental"` Iceberg tables
  (`iceberg: { bucketName: vars.silver_bucket, tableFolderRoot: "iceberg" }` — top-level, camelCase in
  core 3.0.71), tagged by source, filtered with `snapshot.filter()`; data-quality rules go in `assertions`.
- `workflows/cubelake-daily.yaml` — quote every `${...}` that sits inside `[...]`/`{...}` or contains `": "`.
- `infra/terraform/` — Dataform repo needs the `google-beta` provider. Bronze external table schemas are
  in `schemas/*.json`; keep them in sync with the SQLX models.

## Commands

```bash
just test               # pytest + import-linter (extract/)
just dataform-compile   # offline SQLX compile
just tf-validate        # terraform fmt -check + validate (no backend)
just check              # everything CI runs
just extract apple-rss 2026-10-11 /tmp/lake
```

## Naming

Projects `prj-<d|p>-cubelake-<rand>`; buckets `cbl-<d|p>-<bronze|silver>-<rand>`; datasets `<layer>_<source>`;
raw paths `<source>/<dataset>/snapshot_date=D/`; single region `europe-central2`.
