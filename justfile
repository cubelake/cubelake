# cubelake — local checks (the same ones CI runs). Cloud runs need a GCP project; see README.

default:
    @just --list

# Python extract: tests + module-boundary check
test:
    cd extract && uv run pytest -q && uv run lint-imports

# Compile the Dataform project (no GCP needed)
dataform-compile date="2026-01-01":
    npx -y @dataform/cli@3.0.71 compile --vars=snapshot_date={{ date }},silver_bucket=local-bucket

# Terraform formatting + static validation (no GCP needed)
tf-validate:
    cd infra/terraform && terraform fmt -check -recursive && terraform init -backend=false -input=false >/dev/null && terraform validate

# Build the Cloud Run job image
image:
    docker build -t cubelake-extract:local extract

# Run one extract locally into a folder, e.g. `just extract apple-rss 2026-10-11 /tmp/lake`
extract source date root="/tmp/cubelake-lake":
    cd extract && APPLE_RSS_BRONZE_URI={{ root }}/apple_rss/top_charts APPLE_ITUNES_BRONZE_URI={{ root }}/apple_itunes/lookup uv run cubelake-extract {{ source }} --date {{ date }}

# Everything CI checks
check: test dataform-compile tf-validate
