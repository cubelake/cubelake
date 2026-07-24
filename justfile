# cubelake — common developer commands. Run `just` with no arguments
# to see this list. Requires https://github.com/casey/just.

default:
    @just --list

# Install every workspace package into .venv (plain `uv sync` won't — see README)
setup:
    uv sync --all-packages

# Run the ingestion library test suites
test:
    uv run pytest ingestion-apple-rss/tests/ ingestion-apple-itunes/tests/ -v

# --- Airflow (Docker Compose), delegates to infra/appstore-dags/justfile ---

# First-time setup: DB migration + admin user
airflow-init:
    just -f infra/appstore-dags/justfile init

# Start the full Airflow stack
airflow-up:
    just -f infra/appstore-dags/justfile up

# Stop the Airflow stack
airflow-down:
    just -f infra/appstore-dags/justfile down

# Follow Airflow container logs
airflow-logs:
    just -f infra/appstore-dags/justfile logs

# --- dbt ---

# Verify the DuckDB connection and Azure secrets
dbt-debug:
    uv run --env-file .env dbt debug --project-dir appstore-transform

# Run all models for a given snapshot date, e.g. `just dbt-run 2026-07-24`
dbt-run date:
    uv run --env-file .env dbt run --project-dir appstore-transform --vars '{"snapshot_date": "{{ date }}"}'

# Run only the gold models for a given snapshot date
dbt-run-gold date:
    uv run --env-file .env dbt run --project-dir appstore-transform --select marts/gold --vars '{"snapshot_date": "{{ date }}"}'

# Run dbt tests
dbt-test:
    uv run --env-file .env dbt test --project-dir appstore-transform
