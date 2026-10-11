# cubelake — every service is an independent uv project; this file only fans out to them.
# Requires https://github.com/casey/just.

services := "apple-rss apple-itunes appstore-analytics"

default:
    @just --list

# Install each service's own environment (services/<name>/.venv)
setup:
    for s in {{ services }}; do (cd services/$s && uv sync); done

# Run every service's tests
test:
    for s in {{ services }}; do echo "== $s"; (cd services/$s && uv run pytest -q) || exit 1; done

# Build every service image
images:
    for s in {{ services }}; do docker build -t $s:local services/$s; done

# --- Airflow runtime (platform/airflow) ---
airflow-init:
    just -f platform/airflow/justfile init
airflow-up:
    just -f platform/airflow/justfile up
airflow-down:
    just -f platform/airflow/justfile down
airflow-logs:
    just -f platform/airflow/justfile logs
