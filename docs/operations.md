# Operations

## Locally (no cloud)

You need [uv](https://docs.astral.sh/uv/), [just](https://github.com/casey/just), Node 20+, Terraform 1.9+ and Docker.

```bash
just check                                   # everything CI checks
just test                                    # pytest + import-linter
just dataform-compile 2026-10-11             # compile SQLX for a given day
just tf-validate                             # terraform fmt + validate
just ingest apple-rss 2026-10-11 /tmp/lake   # real request to Apple into a local folder
just image                                   # Docker image for local testing
```

`apple-itunes` will not run locally: it needs the `silver_apple_rss.top_apps` table in BigQuery.

Ingest is configured only through environment variables:

| Variable | Example |
| --- | --- |
| `APPLE_RSS_BRONZE_URI` | `gs://cbl-d-bronze-7f3c/apple_rss/top_charts` or a local path |
| `APPLE_ITUNES_BRONZE_URI` | `gs://cbl-d-bronze-7f3c/apple_itunes/lookup` |
| `APPLE_ITUNES_TOP_APPS_TABLE` | `prj-d-cubelake-a1b2.silver_apple_rss.top_apps` |

In the cloud these variables are set by Terraform (`infra/terraform/ingest.tf`); no `.env` files are needed.

## Deploying

Initial setup is described step by step in [owner-tasks.md](owner-tasks.md). Subsequent changes:

| What changed | What to do |
| --- | --- |
| SQLX (`definitions/`) | merge into `main`; Dataform picks up `main` on the next run |
| Python (`src/`) | build a `linux/amd64` image, push it tagged with the git SHA, then `terraform apply -var ingest_image_tag=<sha>` |
| `workflows/*.yaml` or `infra/terraform/` | `terraform apply` |

Until CD is set up, all of this is done by hand. Later GitHub Actions will do it via WIF.

```bash
SHA=$(git rev-parse --short HEAD)
IMAGE=$(terraform -chdir=infra/terraform output -raw ingest_image)
docker build --platform linux/amd64 -t "$IMAGE:$SHA" . && docker push "$IMAGE:$SHA"
terraform -chdir=infra/terraform apply -var ingest_image_tag="$SHA"
```

> On Apple Silicon Macs `--platform linux/amd64` is **required**, otherwise Cloud Run will not start the image.

## Running by hand

```bash
# whole pipeline for today (UTC)
gcloud workflows run cubelake-daily --location europe-central2

# for a specific day (re-run or backfill)
gcloud workflows run cubelake-daily --location europe-central2 --data='{"snapshot_date":"2026-10-11"}'

# a single ingest only
gcloud run jobs execute cubelake-ingest --region europe-central2 --args=apple-rss,--date,2026-10-11 --wait
```

Re-running is safe: bronze overwrites the files of its day, and silver MERGEs by key.

**Important:** Apple serves only the current charts. If you run ingest for a past date, today's chart
gets written under that date. Running with `snapshot_date` only makes sense to re-run today or
yesterday.

**Rebuild silver for all days** (after the Azure migration or after changing SQL):

```bash
gcloud workflows run cubelake-daily --location europe-central2 --data='{"rebuild_silver": true}'
```

Ingest does not run in this mode. Dataform compiles with an empty `snapshot_date`, reads all of bronze and
MERGEs into silver. If you changed a silver table's schema (columns, key), first drop the table or
run the tag with "full refresh" in the Dataform console.

## Where to look when something breaks

| What | Where |
| --- | --- |
| Pipeline runs | Console → Workflows → `cubelake-daily` → Executions |
| Ingest logs | Console → Cloud Run → Jobs → `cubelake-ingest` → Logs (lines `Batch i/N: ok=…, failed=…`, `Wrote X/Y`) |
| Dataform runs and SQL errors | Console → Dataform → `cubelake` → Workflow execution logs |
| Failed quality check | query the view in `dataform_assertions`: it returns the bad rows |
| Bronze files | `gcloud storage ls gs://<bronze>/apple_rss/top_charts/snapshot_date=2026-10-11/` |

### Common errors

| Symptom | Cause / what to do |
| --- | --- |
| `apple-rss` logs `Wrote 200/350` | Apple RSS often responds with `ReadTimeout` and `502`. Whatever was downloaded gets written; the rest is lost for that day. If nothing was downloaded, the job fails. Re-run the day. |
| `apple-itunes`: `No charted apps …` | silver for that day is empty: the `apple_rss_silver` step failed or bronze is empty |
| Dataform: `Cannot query … without a filter over column snapshot_date` | the model has no `${snapshot.filter(...)}` on the bronze table |
| New bronze files are not visible in BigQuery | the BigLake metadata cache refreshes within 4 hours; you can run `CALL BQ.REFRESH_EXTERNAL_METADATA_CACHE('<project>.bronze_apple_rss.top_charts')` |
| Cloud Run: `exec format error` | the image was built for arm64; rebuild with `--platform linux/amd64` |

## Adding a new source

Example: source `google_play`.

1. **Ingest:**
   - create `src/cubelake_ingest/google_play/` with `config.py` (env `GOOGLE_PLAY_*`) and
     `ingest.py` (`ingest(settings, snapshot_date)`); write via `core.bronze` and `core.storage`;
   - add a branch in `cli.py`;
   - add the module to the `independence` contract in `pyproject.toml`;
   - add tests in `tests/google_play/`.
2. **Bronze:**
   - schema `infra/terraform/schemas/bronze_google_play_<dataset>.json`;
   - datasets `bronze_google_play` and `silver_google_play` and an entry in `bronze_tables` in `bigquery.tf`;
   - env variable in `ingest.tf`;
   - `sa-dataform` permissions in `dataform.tf`.
3. **Silver:**
   - `definitions/sources/google_play/google_play.js` (declare);
   - `definitions/sources/google_play/google_play_<table>.sqlx` with `tags: ["google_play"]`.
4. **Orchestration:** steps `google_play_bronze` and `google_play_silver` in `workflows/cubelake-daily.yaml`.
5. Check: `just check`.

## Costs (rough)

At the current volume (a few hundred files of ~100 KB per day) everything fits in the free tier or costs
pennies:
- Cloud Run job: a few minutes per day;
- BigQuery on-demand: queries filter by partition; the MERGE into silver also touches only the day being processed
  (`updatePartitionFilter`), so cost does not grow with the table;
- Workflows: dozens of steps per day;
- GCS: gigabytes.

Still, set up a budget with alerts, see [owner-tasks.md](owner-tasks.md).
