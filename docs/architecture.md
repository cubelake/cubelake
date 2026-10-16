# Architecture

Cubelake collects Apple App Store data and lays it out following the
[Google Cloud Lakehouse](https://docs.cloud.google.com/lakehouse/docs/key-concepts) (medallion) pattern.
Two layers are in scope right now — **bronze** and **silver**. Gold (joins, marts) comes later.

## ELT: who does what

| Step | What it does | Built with | Code |
| --- | --- | --- | --- |
| **E + L** (ingest) | Fetches API responses and stores them as-is in the bronze bucket | Python, Cloud Run job `cubelake-ingest` | `src/cubelake_ingest/` |
| **T** (transform) | Turns bronze into typed silver tables and checks quality | Dataform (SQLX) | `definitions/`, `includes/` |
| Orchestration | Runs ingest → Dataform for each source, in order, every day | Cloud Scheduler + Cloud Workflows | `workflows/cubelake-daily.yaml` |
| Infrastructure | Everything above plus buckets, datasets, IAM | Terraform | `infra/terraform/` |

Why these technologies: this is what Google's documentation recommends for a serverless lakehouse. There is
no VM, Airflow, dbt or DuckDB — nothing to patch and nothing to pay for while nothing is running.

## Layers

| Layer | Meaning at Google | In this project | Storage |
| --- | --- | --- | --- |
| bronze | raw: data as received | Apple RSS / iTunes lookup responses | NDJSON in GCS → BigLake external tables in BigQuery |
| silver | cleansed: cleaned, typed | one row per entity per day | Apache Iceberg managed tables in BigQuery (files in our bucket) |
| gold | curated: business marts | **not yet** | — |

How data is structured in each layer is described in [data.md](data.md).

## Daily flow

```text
Cloud Scheduler  "17 6 * * *" UTC
  └─ Workflows cubelake-daily (snapshot_date = today in UTC, or the argument)
       1. apple_rss_bronze     Cloud Run job: cubelake-ingest apple-rss --date D
                               → gs://cbl-<env>-bronze-<rand>/apple_rss/top_charts/snapshot_date=D/*.json
       2. apple_rss_silver     Dataform: compile(main, vars) → run tag "apple_rss"
                               → silver_apple_rss.top_apps (+ assertions)
       3. apple_itunes_bronze  Cloud Run job: cubelake-ingest apple-itunes --date D
                               (reads app_id from silver_apple_rss.top_apps for day D)
                               → gs://…/apple_itunes/lookup/snapshot_date=D/*.json
       4. apple_itunes_silver  Dataform: run tag "apple_itunes"
                               → silver_apple_itunes.app_details (+ assertions)
```

Steps run strictly in sequence: iTunes needs the finished RSS silver. If a step fails, the whole workflow
stops with an error and the remaining steps do not run.

## Components

### Ingest (Python)

- One package `cubelake_ingest`, one image and one Cloud Run job. The source is chosen by argument:
  `cubelake-ingest <apple-rss|apple-itunes> --date YYYY-MM-DD`.
- `core/` — shared code:
  - `http.py` — async GET in batches of 10 with a 4 s pause, 15 s timeout, 2 retries;
  - `bronze.py` — record format;
  - `storage.py` — writes via fsspec: `gs://…` in the cloud, a local path in tests.
- `apple_rss/`, `apple_itunes/` — one module per source, each with its own `config.py` (env `APPLE_RSS_*`,
  `APPLE_ITUNES_*`). Sources **do not import each other**, and `core` does not import sources.
  `import-linter` enforces this in CI.
- A new source is a new sibling folder. The steps are in [operations.md](operations.md#adding-a-new-source).

### Transform (Dataform)

- The project lives at the **repository root** (`workflow_settings.yaml`) because managed Dataform cannot
  read a project from a subdirectory.
- Layout follows [Google's recommendations](https://docs.cloud.google.com/dataform/docs/best-practices-repositories):
  - `definitions/sources/<source>/<source>.js` — bronze table declaration;
  - `definitions/sources/<source>/<source>_<table>.sqlx` — silver model (`name:` sets the table name);
  - later `definitions/intermediate/` (joins) and `definitions/outputs/<entity>/` (gold).
- Silver models are built like this:
  - `type: "incremental"` with `uniqueKey`, i.e. MERGE: re-running a day never duplicates anything;
  - Iceberg (`iceberg: { bucketName, tableFolderRoot: "iceberg" }`);
  - partitioned by `snapshot_date`, clustered by `country, feed_type`.
- Variables (`vars`) are passed by the workflow at compile time:
  - `snapshot_date` — which day to process; empty = all days;
  - `silver_bucket`.
- Quality checks live in `assertions` inside the model: not null, key uniqueness, accepted
  values. If a check fails, the whole workflow fails.

### Orchestration (Workflows + Scheduler)

- `workflows/cubelake-daily.yaml` — the main flow and two subworkflows:
  - `ingest` starts the Cloud Run job and waits for it to finish;
  - `dataform` compiles the `main` branch, runs the requested tag and polls its status every 20 s.
- Terraform passes the environment variables `REGION`, `INGEST_JOB`, `DATAFORM_REPOSITORY`,
  `SILVER_BUCKET` into the workflow.
- Scheduler calls the workflow with an empty argument, so the date is taken in UTC.

### Infrastructure (Terraform, `infra/terraform/`)

| File | What it creates |
| --- | --- |
| `versions.tf` | google and google-beta providers (Dataform is beta-only), state in GCS |
| `main.tf` | API enablement, random name suffix |
| `storage.tf` | bronze bucket (versioned, Nearline after 90 days) and silver bucket |
| `bigquery.tf` | datasets, BigLake connection `lake`, default Iceberg connection, bronze external tables (schemas in `schemas/*.json`) |
| `ingest.tf` | Artifact Registry `cubelake`, `sa-ingest`, Cloud Run job |
| `dataform.tf` | Dataform repository (pulls code from GitHub, token in Secret Manager), Dataform service agent, `sa-dataform` |
| `orchestration.tf` | `sa-workflows`, workflow, Scheduler |

## Security

- **No service account keys.** Everything in the cloud runs as its own SA. CD from GitHub will use
  Workload Identity Federation, also keyless.
- **Least privilege:**

  | Service account | Can |
  | --- | --- |
  | `sa-ingest` | write objects to the bronze bucket, read `silver_apple_rss`, run BigQuery jobs |
  | `sa-dataform` | read bronze datasets, write silver and `dataform_assertions`, create Iceberg tables via connection `lake` |
  | SA of connection `lake` | read the bronze bucket, write the silver bucket (BigQuery's actual file I/O) |
  | `sa-workflows` | run only the `cubelake-ingest` job, use Dataform, write logs |

- Buckets: uniform bucket-level access, public access blocked (`public_access_prevention = enforced`).
- Bucket names do not contain the project name and end with a random suffix, so they are hard to guess.
- Secrets live only in Secret Manager (the GitHub token for Dataform). There are no secrets in the repository;
  `gitleaks` checks this in CI. `.gitleaksignore` lists three old local Airflow keys from git history;
  they are not used anywhere.
- The image runs as an unprivileged user (uid 10001); only `pyproject.toml`, `uv.lock` and `src/` go into
  the image.

## CI (`.github/workflows/ci.yml`)

Runs on every PR and push to `main`. No cloud needed.

| Job | Checks |
| --- | --- |
| `python` | `uv sync --locked`, pytest, import-linter, Docker image build |
| `dataform` | SQLX compilation; fails on compile errors |
| `terraform` | `fmt -check`, `validate` |
| `secrets` | gitleaks CLI over the whole git history (not `gitleaks-action`: it needs a paid license for organizations) |

CD (build and push the image, `terraform apply`) comes after the GCP project is created.

## What is verified and what is not

Verified offline: tests, module boundaries, Dataform compilation, `terraform validate`, image build,
a real Apple RSS pull into a local folder.

**Not verified until GCP exists:**
- SQL in the BigQuery dialect (hand-ported from DuckDB);
- Iceberg table creation by Dataform;
- `ALTER PROJECT … default_cloud_resource_connection_id`;
- Workflows syntax;
- sufficiency of IAM permissions.

The first cloud run will almost certainly surface a few errors that will need fixing.
