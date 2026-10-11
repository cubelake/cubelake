# cubelake platform. Services and contracts are separate repos cloned next to this file.
# Requires https://github.com/casey/just.

services := "apple-rss apple-itunes appstore-analytics"
org := "https://github.com/Cubelake"

default:
    @just --list

# Clone (or update) every service repo into services/ and the contracts repo into contracts/
clone:
    for s in {{ services }}; do [ -d services/$s/.git ] && git -C services/$s pull --ff-only || git clone {{ org }}/$s.git services/$s; done
    [ -d contracts/.git ] && git -C contracts pull --ff-only || git clone {{ org }}/cubelake-contracts.git contracts

# Install each service's own environment (services/<name>/.venv)
setup:
    for s in {{ services }}; do (cd services/$s && uv sync); done

# Run every service's tests and the contract tests
test:
    for s in {{ services }}; do echo "== $s"; (cd services/$s && uv run pytest -q) || exit 1; done
    echo "== contracts"; cd contracts && uv run pytest -q

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
