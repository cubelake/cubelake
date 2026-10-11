#!/usr/bin/env bash
# One-off: copy the old Azure (ADLS Gen2) bronze into the GCS bronze bucket, remapping paths.
#
#   azure://bronze/appstore_rss/snapshot_date=D/<country>_<feed>.json
#     → gs://<bronze>/apple_rss/top_charts/snapshot_date=D/<country>_<feed>.json
#   azure://bronze/appstore_itunes/snapshot_date=D/<country>_<feed>.json
#     → gs://<bronze>/apple_itunes/lookup/snapshot_date=D/<country>_<feed>.json
#
# File contents are copied byte for byte (same record format; only `_source` differs:
# "ingestion-apple-rss" vs "apple-rss", which silver does not use).
# Runs server-side with Storage Transfer Service; objects already in GCS are never overwritten,
# so days collected by the new pipeline win. Safe to re-run.
#
# Usage:
#   AZURE_ACCOUNT=<storage account> scripts/migrate_azure_bronze.sh [--dry-run]
# Optional env: AZURE_CONTAINER (default bronze), BRONZE_BUCKET (default: terraform output),
#               GOOGLE_CLOUD_PROJECT (default: gcloud config).
# The SAS token (Read + List on the container) is asked interactively and only written to a
# temporary 0600 file that is deleted on exit.
set -euo pipefail

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

: "${AZURE_ACCOUNT:?set AZURE_ACCOUNT to the Azure storage account name}"
AZURE_CONTAINER="${AZURE_CONTAINER:-bronze}"
PROJECT="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BRONZE_BUCKET="${BRONZE_BUCKET:-$(terraform -chdir="$REPO_ROOT/infra/terraform" output -raw bronze_bucket)}"
[[ -n "$PROJECT" && -n "$BRONZE_BUCKET" ]] || { echo "project or bronze bucket unknown" >&2; exit 1; }

# old Azure prefix → new GCS prefix (must match infra/terraform/bigquery.tf bronze_tables)
MAPPINGS=(
  "appstore_rss/:apple_rss/top_charts/"
  "appstore_itunes/:apple_itunes/lookup/"
)

echo "Project:       $PROJECT"
echo "From (Azure):  https://$AZURE_ACCOUNT.blob.core.windows.net/$AZURE_CONTAINER/"
echo "To (GCS):      gs://$BRONZE_BUCKET/"
for m in "${MAPPINGS[@]}"; do echo "  ${m%%:*}  →  ${m#*:}"; done
if $DRY_RUN; then echo "Dry run: nothing created."; exit 0; fi

read -r -s -p "Azure SAS token (Read + List): " SAS && echo
[[ -n "$SAS" ]] || { echo "empty SAS token" >&2; exit 1; }
CREDS="$(mktemp)"
trap 'rm -f "$CREDS"' EXIT
chmod 600 "$CREDS"
printf '{"sasToken": "%s"}' "${SAS#\?}" >"$CREDS"
unset SAS

gcloud services enable storagetransfer.googleapis.com --project "$PROJECT"
# Grants the Storage Transfer service agent write access to buckets in this project.
gcloud transfer authorize --add-missing --project "$PROJECT"

for m in "${MAPPINGS[@]}"; do
  src="${m%%:*}" dst="${m#*:}"
  job=$(gcloud transfer jobs create \
    "https://$AZURE_ACCOUNT.blob.core.windows.net/$AZURE_CONTAINER/$src" \
    "gs://$BRONZE_BUCKET/$dst" \
    --source-creds-file="$CREDS" \
    --overwrite-when=never \
    --description="cubelake: Azure $src → $dst" \
    --project "$PROJECT" --format='value(name)')
  echo "Started $job ($src → $dst); waiting…"
  gcloud transfer jobs monitor "$job" --project "$PROJECT"
done

echo
echo "Days now in GCS:"
for m in "${MAPPINGS[@]}"; do
  dst="${m#*:}"
  n=$(gcloud storage ls "gs://$BRONZE_BUCKET/$dst" | grep -c 'snapshot_date=' || true)
  echo "  $dst  $n days"
done

# Make BigLake see the new files now instead of within the 4 h cache window.
for t in bronze_apple_rss.top_charts bronze_apple_itunes.lookup; do
  bq query --project_id "$PROJECT" --use_legacy_sql=false --quiet \
    "CALL BQ.REFRESH_EXTERNAL_METADATA_CACHE('$PROJECT.$t')" >/dev/null
done

cat <<EOF

Bronze copied. Rebuild silver for every day:
  gcloud workflows run cubelake-daily --location europe-central2 --data='{"rebuild_silver": true}'
EOF
