# cubelake platform. Services and contracts are separate repos cloned NEXT TO this repo (../<name>).
# Requires https://github.com/casey/just.

services := "apple-rss apple-itunes appstore-analytics"
org := "https://github.com/Cubelake"
repos := ".."

default:
    @just --list

# Clone (or update) every service repo and the contracts repo next to this one
clone:
    for r in {{ services }} cubelake-contracts; do [ -d {{ repos }}/$r/.git ] && git -C {{ repos }}/$r pull --ff-only || git clone {{ org }}/$r.git {{ repos }}/$r; done

# Install each service's own environment (../<name>/.venv)
setup:
    for s in {{ services }}; do (cd {{ repos }}/$s && uv sync); done

# Run every service's tests and the contract tests
test:
    for s in {{ services }}; do echo "== $s"; (cd {{ repos }}/$s && uv run pytest -q) || exit 1; done
    echo "== cubelake-contracts"; cd {{ repos }}/cubelake-contracts && uv run pytest -q

# Build every service image
images:
    for s in {{ services }}; do docker build -t $s:local {{ repos }}/$s; done

# --- Airflow runtime (platform/airflow) ---
airflow-init:
    just -f platform/airflow/justfile init
airflow-up:
    just -f platform/airflow/justfile up
airflow-down:
    just -f platform/airflow/justfile down
airflow-logs:
    just -f platform/airflow/justfile logs
