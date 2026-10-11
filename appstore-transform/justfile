default:
    @just --list

# Verify the DuckDB connection and Azure secrets
dbt_ct:
    uv run --env-file .env dbt debug --profiles-dir .

# Run all models for a given snapshot date, e.g. `just run 2026-07-24`
run date:
    uv run --env-file .env dbt run --vars '{"snapshot_date": "{{ date }}"}'

# Run only the gold models for a given snapshot date
run-gold date:
    uv run --env-file .env dbt run --select marts/gold --vars '{"snapshot_date": "{{ date }}"}'

# Run dbt tests
test:
    uv run --env-file .env dbt test
