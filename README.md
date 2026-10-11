# Cubelake

> Apple App Store data on Google Cloud Lakehouse: raw API responses → normalized tables.

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![BigQuery](https://img.shields.io/badge/BigQuery-Iceberg-669DF6?logo=googlebigquery&logoColor=white)
![Dataform](https://img.shields.io/badge/Dataform-3.0-4285F4?logo=googlecloud&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-1.9+-844FBA?logo=terraform&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

Cubelake follows the [Google Cloud Lakehouse](https://docs.cloud.google.com/lakehouse/docs/lakehouse-basics)
medallion pattern. Current scope is two layers:

| Layer | Where | What |
| --- | --- | --- |
| **bronze** (raw) | Cloud Storage, NDJSON, `snapshot_date=YYYY-MM-DD/` | API responses exactly as received; exposed to BigQuery as BigLake external tables |
| **silver** (normalized) | Apache Iceberg managed tables in BigQuery (data in our bucket) | one clean, typed row per entity per day, with data-quality assertions |

Gold (joined, business-level marts) comes later.

## Pipeline

```text
Cloud Scheduler (daily 06:17 UTC) → Cloud Workflows "cubelake-daily"
  1. Cloud Run job  cubelake-extract apple-rss    → gs://cbl-<env>-bronze-<rand>/apple_rss/top_charts/snapshot_date=D/
  2. Dataform       tag apple_rss                 → silver_apple_rss.top_apps
  3. Cloud Run job  cubelake-extract apple-itunes → gs://…/apple_itunes/lookup/snapshot_date=D/
                    (app ids read from silver_apple_rss.top_apps)
  4. Dataform       tag apple_itunes              → silver_apple_itunes.app_details
```

Re-process a day: run the workflow with `{"snapshot_date": "2026-10-11"}`. Silver tables are incremental
(MERGE on their key), so re-runs are idempotent.

## Data

| Dataset.table | Type | Grain |
| --- | --- | --- |
| `bronze_apple_rss.top_charts` | BigLake external (NDJSON) | one chart response per country × free/paid per day |
| `bronze_apple_itunes.lookup` | BigLake external (NDJSON) | one lookup response per country × free/paid per day |
| `silver_apple_rss.top_apps` | Iceberg managed | app × chart position × country × feed × day |
| `silver_apple_itunes.app_details` | Iceberg managed | app × country × feed × day |

Bronze tables require a `snapshot_date` filter. Silver tables are partitioned by `snapshot_date` and
clustered by `country, feed_type`.

## Repository layout

Modular monolith — one repo, clear boundaries per source:

```text
extract/                 Python (uv) — Cloud Run job image `cubelake-extract <source> --date D`
  src/cubelake_extract/
    core/                http fetching, bronze record format, storage writes
    apple_rss/           top charts: countries, feed URLs, extract
    apple_itunes/        lookups for charted apps
workflow_settings.yaml   Dataform project (must be at the repo root for managed Dataform)
definitions/             Dataform: sources (bronze), apple_rss/, apple_itunes/ (silver)
includes/                Dataform helpers
workflows/               Cloud Workflows pipeline
infra/terraform/         all GCP resources
.github/workflows/ci.yml tests, import boundaries, dataform compile, terraform validate, gitleaks
```

`apple_rss` and `apple_itunes` never import each other (enforced by `import-linter`); both may use `core`.

## Naming

| Thing | Convention | Example |
| --- | --- | --- |
| Projects | `prj-<d\|p>-cubelake-<rand>` ([Google blueprint](https://docs.cloud.google.com/architecture/blueprints/security-foundations/summary)) | `prj-p-cubelake-a1b2` |
| Buckets | `cbl-<d\|p>-<layer>-<rand>` — no project name, hard to guess ([GCS best practices](https://docs.cloud.google.com/storage/docs/best-practices)) | `cbl-p-bronze-7f3c` |
| Raw paths | `<source>/<dataset>/snapshot_date=YYYY-MM-DD/<country>_<feed>.json` | `apple_rss/top_charts/snapshot_date=2026-10-11/us_top_free.json` |
| Datasets | `<layer>_<source>` | `silver_apple_rss` |
| Iceberg data | `gs://cbl-<env>-silver-<rand>/iceberg/<dataset>/<table>/` | |
| Region | everything in one region (buckets and datasets must match) | `europe-central2` |

## Local development

Prerequisites: [uv](https://docs.astral.sh/uv/), [just](https://github.com/casey/just), Node 20+, Terraform 1.9+, Docker.

```bash
just test              # extract tests + module boundaries
just dataform-compile  # compile the SQLX project offline
just tf-validate       # terraform fmt + validate offline
just check             # all of the above (what CI runs)
just extract apple-rss 2026-10-11 /tmp/lake   # real API pull into a local folder
```

Running Dataform or the workflow needs a GCP project.

## Deploying (first time)

1. Create the GCP project (`prj-d-cubelake-<rand>`) with billing; `gcloud auth application-default login`.
2. Create a GCS bucket for Terraform state and a Secret Manager secret `dataform-github-token`
   (read-only GitHub token for this repo).
3. `cd infra/terraform && cp terraform.tfvars.example terraform.tfvars` and fill it in.
4. `terraform init -backend-config="bucket=<state-bucket>" && terraform apply`.
5. Build and push the extract image to the `extract_image` output, then re-apply with `extract_image_tag`.

CD from GitHub Actions (Workload Identity Federation, no keys) comes next.

## License

[MIT](LICENSE)
